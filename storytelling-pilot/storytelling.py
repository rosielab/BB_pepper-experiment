# %%
# -*- coding: utf-8 -*-
import numpy as np
from pathlib import Path
import soundfile as sf
import torch
import sys

import os
import time

from types import SimpleNamespace
import json, torch


from matcha.hifigan.config import v1
from matcha.hifigan.denoiser import Denoiser
from matcha.hifigan.env import AttrDict
from matcha.hifigan.models import Generator as HiFiGAN
from matcha.models.matcha_tts import MatchaTTS
from matcha.text import sequence_to_text, text_to_sequence
from matcha.utils.utils import get_user_data_dir, intersperse, assert_model_downloaded

import emoji

import threading
import numpy as np
import sounddevice as sd
import wavio
import sys
import tty
import termios
import shutil
from datetime import datetime
import whisper

from inserts_mapping import inserts_dict as inserts

BASE_DIR = Path(__file__).resolve().parent
RUN_META_PATH = BASE_DIR / ".current_run.json"
ARCHIVE_ROOT = BASE_DIR / "overallresults"

WORK_OUTPUTS = BASE_DIR / "outputs"
WORK_RESULTS = BASE_DIR / "results"
WORK_OUTPUTS.mkdir(parents=True, exist_ok=True)
WORK_RESULTS.mkdir(parents=True, exist_ok=True)

VOICE = 'emoji'
SCRIPT_PATH = "/home/rosie/Documents/BBPepper/BB_pepper-experiment/storytelling-pilot/frog_script_eye_roll.txt"
WAV_PATH = str(WORK_OUTPUTS)
############################ TTS PARAMETERS ############################################################################
TTS_MODEL_PATH = os.path.join(os.path.dirname(__file__), "matcha_state_dict.pt")
#TTS_MODEL_PATH = os.path.join(os.path.dirname(__file__), "emoji-hri-paige-inference.ckpt")
HPARAMS_PATH = os.path.join(os.path.dirname(__file__), "matcha_hparams.json")
SPEAKING_RATE = 0.9
STEPS = 10
LANGUAGE = "en"
# hifigan_univ_v1 is suggested, unless the custom model is trained on LJ Speech
VOCODER_NAME= "hifigan_univ_v1"
TTS_TEMPERATURE = 0.667
VOCODER_URLS = {
    "hifigan_T2_v1": "https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/generator_v1",  # Old url: https://drive.google.com/file/d/14NENd4equCBLyyCSke114Mv6YR_j_uFs/view?usp=drive_link
    "hifigan_univ_v1": "https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/g_02500000",  # Old url: https://drive.google.com/file/d/1qpgI41wNXFcH-iKq1Y42JlBC9j0je8PW/view?usp=drive_link
}

#maps the emojis used by the LLM to the speaker numbers from the Matcha-TTS checkpoint
emoji_mapping = {
    '😍' : 107,
    '😡' : 58,
    '😎' : 79,
    '😭' : 103,
    '🙄' : 66,
    '😁' : 18,
    '🙂' : 12,
    '🤣' : 15,
    '😮' : 54,
    '😅' : 22,
    '🤔' : 17
}


####################### ASR SETUP ######################################################################################

ASR_MODEL = "small.en"

########################################################################################################################
class Recorder:
    def __init__(self):
        self.frames = []
        self.recording = False
        self.stream = None

    def start_recording(self, filename, fs=44100, channels=1):
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(callback=self.callback, channels=channels, samplerate=fs)
        self.stream.start()
        print("Recording... Press any key but Enter to stop the recording.")

        # Start a thread to wait for a key press
        stop_thread = threading.Thread(target=self.wait_for_stop)
        stop_thread.start()

        # Wait for the recording to stop
        stop_thread.join()

        self.stream.stop()
        self.stream.close()
        print("Recording stopped.")

        # Check if frames are collected
        if len(self.frames) > 0:
            # Convert frames to a NumPy array
            audio_data = np.concatenate(self.frames, axis=0)
            # Normalize audio data to fit within int16 range
            audio_data = np.clip(audio_data * 32767, -32768, 32767)
            audio_data = audio_data.astype(np.int16)  # Convert to int16

            wavio.write(filename, audio_data, fs, sampwidth=2)
        else:
            print("No audio data recorded.")

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.frames.append(indata.copy())

    def wait_for_stop(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        self.recording = False

def wait_done(wav_path: str, poll=0.05):
    done_path = wav_path + ".done"
    while not os.path.exists(done_path):
        time.sleep(poll)


def process_text(text: str, device: torch.device, language: str):
    cleaners = {
        "en": "english_cleaners2",
        "fr": "french_cleaners",
        "ja": "japanese_cleaners",
        "es": "spanish_cleaners",
        "de": "german_cleaners",
    }
    if language not in cleaners:
        print("Invalid language. Current supported languages: en (English), fr (French), ja (Japanese), de (German).")
        sys.exit(1)

    x = torch.tensor(
        intersperse(text_to_sequence(text, [cleaners[language]])[0], 0),
        dtype=torch.long,
        device=device,
    )[None]
    x_lengths = torch.tensor([x.shape[-1]], dtype=torch.long, device=device)
    x_phones = sequence_to_text(x.squeeze(0).tolist())

    return {"x_orig": text, "x": x, "x_lengths": x_lengths, "x_phones": x_phones}

def to_ns(x):
    if isinstance(x, dict):
        return SimpleNamespace(**{k: to_ns(v) for k, v in x.items()})
    if isinstance(x, list):
        return [to_ns(v) for v in x]
    return x


def load_matcha(weights_path, hparams_path, device):
    with open(hparams_path) as f:
        hparams = json.load(f)

    # patch required by your ckpt (out_size was None)
    if hparams.get("out_size") in (None, "None"):
        hparams["out_size"] = hparams["n_feats"]

    # Wrap ONLY the parts Matcha accesses with dots
    if isinstance(hparams.get("encoder"), dict):
        hparams["encoder"] = to_ns(hparams["encoder"])

    if isinstance(hparams.get("cfm"), dict):
        hparams["cfm"] = to_ns(hparams["cfm"])

    model = MatchaTTS(**hparams)

    state = torch.load(weights_path, map_location=device, weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    return model

#def load_matcha(weights_path, hparams_path, device):
#
#    def to_ns(x):
#        if isinstance(x, dict):
#            return SimpleNamespace(**{k: to_ns(v) for k, v in x.items()})
#        if isinstance(x, list):
#            return [to_ns(v) for v in x]
#        return x
#
#    # Load checkpoint (trusted)
#    ckpt = torch.load(weights_path, map_location=device, weights_only=False)
#
#    # Load JSON hparams as fallback
#    with open(hparams_path) as f:
#        hparams = json.load(f)
#
#    # If Lightning saved the exact training hparams, prefer those
#    if isinstance(ckpt, dict) and "hyper_parameters" in ckpt and isinstance(ckpt["hyper_parameters"], dict):
#        hparams = ckpt["hyper_parameters"]
#
#    # Some ckpts store nested dicts; Matcha expects dot access for encoder/cfm
#    if hparams.get("out_size") in (None, "None"):
#        hparams["out_size"] = hparams["n_feats"]
#
#    if isinstance(hparams.get("encoder"), dict):
#        hparams["encoder"] = to_ns(hparams["encoder"])
#    if isinstance(hparams.get("cfm"), dict):
#        hparams["cfm"] = to_ns(hparams["cfm"])
#
#    model = MatchaTTS(**hparams)
#
#    # Get the actual weights
#    state_dict = ckpt["state_dict"] if isinstance(ckpt, dict) and "state_dict" in ckpt else ckpt
#
#    # Strip common prefixes if present
#    for prefix in ("model.", "tts_model.", "net.", "generator."):
#        if any(k.startswith(prefix) for k in state_dict.keys()):
#            state_dict = {k[len(prefix):]: v for k, v in state_dict.items()}
#            break
#
#    model.load_state_dict(state_dict, strict=True)
#    model.to(device).eval()
#    return model


def load_hifigan(checkpoint_path, device):
    h = AttrDict(v1)
    hifigan = HiFiGAN(h).to(device)
    hifigan.load_state_dict(torch.load(checkpoint_path, map_location=device)["generator"])
    _ = hifigan.eval()
    hifigan.remove_weight_norm()
    return hifigan

def load_vocoder(vocoder_name, checkpoint_path, device):
    vocoder = None
    if vocoder_name in ("hifigan_T2_v1", "hifigan_univ_v1"):
        vocoder = load_hifigan(checkpoint_path, device)
    else:
        raise NotImplementedError(
            f"Vocoder not implemented! define a load_<<vocoder_name>> method for it"
        )

    denoiser = Denoiser(vocoder, mode="zeros")
    return vocoder, denoiser

@torch.inference_mode()
def to_waveform(mel, vocoder, denoiser=None):
    audio = vocoder(mel).clamp(-1, 1)
    if denoiser is not None:
        audio = denoiser(audio.squeeze(), strength=0.00025).cpu().squeeze()

    return audio.cpu().squeeze()

def save_to_folder(filename: str, output: dict, folder: str):
    folder = Path(folder)
    folder.mkdir(exist_ok=True, parents=True)
    sf.write(folder / f"to_play-{filename}.wav", output["waveform"], 22050, "PCM_24")

def play_only_synthesis(device, model, vocoder, denoiser, text, spk, language, i):
    text = text.strip()
    text_processed = process_text(text, device, language)

    output = model.synthesise(
        text_processed["x"],
        text_processed["x_lengths"],
        n_timesteps=STEPS,
        temperature=TTS_TEMPERATURE,
        spks=spk,
        length_scale=SPEAKING_RATE,
    )
    output["waveform"] = to_waveform(output["mel"], vocoder, denoiser)

    output["waveform"] = np.clip(output["waveform"], -1.0, 1.0)

    save_to_folder(i, output, WAV_PATH)

def assert_required_models_available():
    save_dir = get_user_data_dir()
    model_path = TTS_MODEL_PATH

    vocoder_path = save_dir / f"{VOCODER_NAME}"
    assert_model_downloaded(vocoder_path, VOCODER_URLS[VOCODER_NAME])
    return {"matcha": model_path, "vocoder": vocoder_path}

def contains_only_non_emoji(string):
    return all(not emoji.is_emoji(char) for char in string) and len(string.strip()) > 0

def archive_and_clean():
    # Read run metadata (written by pilot.py)
    if RUN_META_PATH.exists():
        meta = json.loads(RUN_META_PATH.read_text())
        run_dir = Path(meta["run_dir"])
    else:
        # fallback if pilot didn't create meta
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = ARCHIVE_ROOT / "unnamed" / ts
        run_dir.mkdir(parents=True, exist_ok=True)

    out_dst = run_dir / "outputs"
    res_dst = run_dir / "results"
    out_dst.mkdir(parents=True, exist_ok=True)
    res_dst.mkdir(parents=True, exist_ok=True)

    # Move working files into archive
    # Move working files into archive (but KEEP chime.wav in outputs/)
    for p in WORK_OUTPUTS.glob("*"):
        if p.name == "chime.wav":
            # keep it in outputs for next run, but also save a copy in the archive
            shutil.copy2(str(p), str(out_dst / p.name))
            continue
        shutil.move(str(p), str(out_dst / p.name))

    for p in WORK_RESULTS.glob("*"):
        shutil.move(str(p), str(res_dst / p.name))

    # Recreate clean working dirs (so VS Code looks empty)
    WORK_OUTPUTS.mkdir(parents=True, exist_ok=True)
    WORK_RESULTS.mkdir(parents=True, exist_ok=True)

    print(f"[ARCHIVE] moved outputs/ + results/ into: {run_dir}")

if __name__ == "__main__":
    try:
        tts_device = "cuda" if torch.cuda.is_available() else "cpu"
        paths = assert_required_models_available()
        
        asr_model = whisper.load_model(ASR_MODEL)

        save_dir = get_user_data_dir() 
    
        tts_model = load_matcha(paths["matcha"], HPARAMS_PATH, tts_device)
        vocoder, denoiser = load_vocoder(VOCODER_NAME, paths["vocoder"], tts_device)
        
        participant_name = input("Enter participant name: ")
        
        spk_greeting = torch.tensor([12], device=tts_device, dtype=torch.long)
        greeting_id = "greeting"
        
        print(f"Synthesizing greeting for {participant_name}...")
        play_only_synthesis(
            tts_device, tts_model, vocoder, denoiser,
            f"Hi {participant_name}. Nice to meet you!", spk_greeting, LANGUAGE, greeting_id
        )
        
        greeting_wav = f"{WAV_PATH}/to_play-{greeting_id}.wav"
        print("Waiting for greeting to play...")
        wait_done(greeting_wav)

        print("\nReady to start!")
        input("Press the [Enter] key to begin the story...")

        with open(SCRIPT_PATH, 'r') as file:
            for i, line in enumerate(file):
                print("Insert", i)
                if i in inserts and inserts[i] != "chime":
                    spk = torch.tensor([12], device=tts_device, dtype=torch.long)

                    q_id = f"q-{i}"
                    #print(f"[GEN] line {i}: {clean_line[:60]}{'...' if len(clean_line) > 60 else ''}")
                    play_only_synthesis(tts_device, tts_model, vocoder, denoiser, inserts[i], spk, LANGUAGE, q_id)

                    q_wav = f"{WAV_PATH}/to_play-{q_id}.wav"
                    
                    print("waiting")

                    wait_done(q_wav)
                    
                    #wait for response to generate the next
                    os.environ["ALSA_PCM_CARD"] = "0"
                    # wait for response to generate the next (record using ALSA directly; avoids PyAudio crash)
                    print("Now recording 🎤 (Press Enter to stop)")

                    import subprocess, signal
                    rec_cmd = ["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", "16000", "-c", "1", f"./results/output-{i}.wav"]
                    proc = subprocess.Popen(rec_cmd)
                    input()  # press Enter to stop recording
                    proc.send_signal(signal.SIGINT)
                    proc.wait()

                    #recorder = Recorder()
                    
                    #print("Now recording 🎤")
                    #recorder.start_recording(f"./results/output-{i}.wav")

                    result = asr_model.transcribe(f"./results/output-{i}.wav")
                    result = result['text']

                    print(f'speaker said: {result}')
                    
                    with open("./results/transcription.txt", "a") as transcripts:
                        transcripts.write(result + "\n")
                    
                    #feedback
                    fb_id = f"fb-{i}"
                    if inserts[i] == "Where do you think the frog is?":
                        play_only_synthesis(
                            tts_device, tts_model, vocoder, denoiser,
                            "Let's go see!", spk, LANGUAGE, fb_id
                        )
                    if inserts[i] == "Have you ever seen a deer before?":
                        play_only_synthesis(
                            tts_device, tts_model, vocoder, denoiser,
                            "That's interesting", spk, LANGUAGE, fb_id
                        )
                    if inserts[i] == "Let's call for the frog together":
                        play_only_synthesis(
                            tts_device, tts_model, vocoder, denoiser,
                            "Sounds great!", spk, LANGUAGE, fb_id
                        )
                    if inserts[i] == "What do you think is in the hollow":
                        play_only_synthesis(
                            tts_device, tts_model, vocoder, denoiser,
                            "It's an owl!", spk, LANGUAGE, fb_id
                        )
                    if inserts[i] == "What sounds do you think the frog makes?":
                        play_only_synthesis(
                            tts_device, tts_model, vocoder, denoiser,
                            "I love it!", spk, LANGUAGE, fb_id
                        ),
                    if inserts[i] == "What do you think they heard?":
                        play_only_synthesis(
                            tts_device, tts_model, vocoder, denoiser,
                            "Cool!", spk, LANGUAGE, fb_id
                        )

                    fb_wav = f"{WAV_PATH}/to_play-{fb_id}.wav"
                    wait_done(fb_wav)


                clean_line = line.strip()
                if VOICE == 'emoji':
                    spk = torch.tensor([12], device=tts_device, dtype=torch.long)
                    for emote in emoji_mapping:
                        if emote in clean_line:
                            spk = torch.tensor([emoji_mapping[emote]], device=tts_device, dtype=torch.long)
                            break
                elif VOICE == 'base':
                    spk = torch.tensor([1], device=tts_device, dtype=torch.long)
                elif VOICE == 'default':
                    spk = torch.tensor([12], device=tts_device, dtype=torch.long)
                else:
                    print("hmmm wrong voice")
                clean_line = emoji.replace_emoji(clean_line, '')
                #matcha cannot handle brackets
                clean_line = clean_line.replace(')', '')
                clean_line = clean_line.replace('(', '')
                play_only_synthesis(tts_device, tts_model, vocoder, denoiser, clean_line, spk, LANGUAGE, i)


        if i+1 in inserts:
            spk = torch.tensor([12], device=tts_device, dtype=torch.long)

            q_id = f"q-{i+1}"
            play_only_synthesis(tts_device, tts_model, vocoder, denoiser, inserts[i+1], spk, LANGUAGE, q_id)

            q_wav = f"{WAV_PATH}/to_play-{q_id}.wav"
                    
            print("waiting")

            wait_done(q_wav)
                    
            #wait for response to generate the next
            recorder = Recorder()
                    
            # record using ALSA directly (avoids PortAudio/sounddevice crash)
            print("Now recording 🎤 (Press Enter to stop)")
            import subprocess, signal
            rec_cmd = ["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", "16000", "-c", "1", f"./results/output-{i}.wav"]
            proc = subprocess.Popen(rec_cmd)
            input()  # press Enter to stop recording
            proc.send_signal(signal.SIGINT)
            proc.wait()
            
            result = asr_model.transcribe(f"./results/output-{i}.wav")
            result = result['text']

            print(f'speaker said: {result}')
                    
            with open("./results/transcription.txt", "a") as transcripts:
                transcripts.write(result + "\n")
                    
            #feedback
            fb_id = f"fb-{i+1}"
            play_only_synthesis(
                tts_device, tts_model, vocoder, denoiser,
                "Great answer!", spk, LANGUAGE, fb_id
            )
            
            spk = torch.tensor([107], device=tts_device, dtype=torch.long)
            
        play_only_synthesis(
            tts_device, tts_model, vocoder, denoiser,
            f"Thank you so much for taking the time to listen to my story {participant_name}!", spk, LANGUAGE, "final"
        )
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Ctrl+C received — archiving what exists so far...")

    finally:
        archive_and_clean()
        print("[DONE] Archived + cleaned working folders.")