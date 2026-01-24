# %%
import numpy as np
from pathlib import Path
import soundfile as sf
import torch
import sys

import os
import time

from types import SimpleNamespace
import json, torch
from matcha.models.matcha_tts import MatchaTTS


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

import whisper

VOICE = 'emoji'
SCRIPT_PATH = "/home/paige/Documents/BB_pepper-experiment/storytelling-pilot/frog_script.txt"
WAV_PATH = "./outputs"
############################ TTS PARAMETERS ############################################################################
TTS_MODEL_PATH = "./matcha_state_dict.pt"
HPARAMS_PATH = "./matcha_hparams.json"
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

if __name__ == "__main__":

    tts_device = "cuda" if torch.cuda.is_available() else "cpu"
    paths = assert_required_models_available()
    
    asr_model = whisper.load_model(ASR_MODEL)

    save_dir = get_user_data_dir() 
 
    tts_model = load_matcha(paths["matcha"], HPARAMS_PATH, tts_device)
    vocoder, denoiser = load_vocoder(VOCODER_NAME, paths["vocoder"], tts_device)
    
    inserts = {
        10:  "Where do you think the frog is?",
        31: "Have you ever seen a deer before?",
        47: "Do you think the frog will be happy with his family?",
    }

    with open(SCRIPT_PATH, 'r') as file:
        for i, line in enumerate(file):
            if i in inserts:
                spk = torch.tensor([12], device=tts_device, dtype=torch.long)

                q_id = f"q-{i}"
                play_only_synthesis(tts_device, tts_model, vocoder, denoiser, inserts[i], spk, LANGUAGE, q_id)

                q_wav = f"{WAV_PATH}/to_play-{q_id}.wav"
                
                print("waiting")

                wait_done(q_wav)
                
                #wait for response to generate the next
                recorder = Recorder()
                
                print("Now recording 🎤")
                recorder.start_recording(f"./results/output-{i}.wav")

                result = asr_model.transcribe(f"./results/output-{i}.wav")
                result = result['text']

                print(f'speaker said: {result}')
                
                with open("./results/transcription.txt", "a") as transcripts:
                    transcripts.write(result + "\n")
                
                #feedback
                fb_id = f"fb-{i}"
                play_only_synthesis(
                    tts_device, tts_model, vocoder, denoiser,
                    "Oh, very interesting.", spk, LANGUAGE, fb_id
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
                
        print("Now recording 🎤")
        recorder.start_recording(f"./results/output-{i}.wav")

        result = asr_model.transcribe(f"./results/output-{i}.wav")
        result = result['text']

        print(f'speaker said: {result}')
                
        with open("transcription.txt", "a") as transcripts:
            transcripts.write(result + "\n")
                
        #feedback
        fb_id = f"fb-{i+1}"
        play_only_synthesis(
            tts_device, tts_model, vocoder, denoiser,
            "Oh, very interesting.", spk, LANGUAGE, fb_id
        )
        
        spk = torch.tensor([107], device=tts_device, dtype=torch.long)
        
        play_only_synthesis(
            tts_device, tts_model, vocoder, denoiser,
            "Thank you so much for taking the time to listen to my story!", spk, LANGUAGE, "final"
        )