# %%
# -*- coding: utf-8 -*-
import numpy as np
from pathlib import Path
import soundfile as sf
import torch
import sys

import os
import re
import time

from types import SimpleNamespace
import torch
from matcha.models.matcha_tts import MatchaTTS
from random import randint


from matcha.hifigan.config import v1
from matcha.hifigan.denoiser import Denoiser
from matcha.hifigan.env import AttrDict
from matcha.hifigan.models import Generator as HiFiGAN
from matcha.models.matcha_tts import MatchaTTS
from matcha.text import sequence_to_text, text_to_sequence
from matcha.utils.utils import get_user_data_dir, intersperse, assert_model_downloaded


import numpy as np
import sys

# PyTorch 2.6 compatibility for trusted Lightning checkpoints
_original_torch_load = torch.load

def torch_load_compat(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

torch.load = torch_load_compat

BASE_DIR = Path(__file__).resolve().parent
RUN_META_PATH = BASE_DIR / ".current_run.json"
ARCHIVE_ROOT = BASE_DIR / "overallresults"

WORK_OUTPUTS = BASE_DIR / "outputs"
WORK_RESULTS = BASE_DIR / "results"
WORK_OUTPUTS.mkdir(parents=True, exist_ok=True)
WORK_RESULTS.mkdir(parents=True, exist_ok=True)

VOICE = 'neutral' # replace with chanel/random/neutral, then ctrl+s to save
SCRIPT_PATH = "/home/rosie/BB_pepper-experiment/storytelling-frog_script/frog_script_emoji.txt"
WAV_PATH = str(WORK_OUTPUTS)
############################ TTS PARAMETERS ############################################################################
#TTS_MODEL_PATH = os.path.join(os.path.dirname(__file__), "matcha_state_dict.pt")
#HPARAMS_PATH = os.path.join(os.path.dirname(__file__), "matcha_hparams.json")
TTS_MODEL_PATH = os.path.join(os.path.dirname(__file__), "chanel-with-neutral.ckpt")
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
# for Chanel
if VOICE == 'chanel':
    emoji_mapping = {
        '😡' : 9,
        '😭' : 8,
        '😁' : 7,
        '🙂' : 6,
        '😮' : 5,
    }


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

def load_matcha(checkpoint_path, device):
    model = MatchaTTS.load_from_checkpoint(checkpoint_path, map_location=device)
    _ = model.eval()
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

# def synthesis(device, model, vocoder, denoiser, text, spk, language, i):
#     text = text.strip()
#     text_processed = process_text(text, device, language)

#     output = model.synthesise(
#         text_processed["x"],
#         text_processed["x_lengths"],
#         n_timesteps=STEPS,
#         temperature=TTS_TEMPERATURE,
#         spks=spk,
#         length_scale=SPEAKING_RATE,
#     )
#     output["waveform"] = to_waveform(output["mel"], vocoder, denoiser)

#     output["waveform"] = np.clip(output["waveform"], -1.0, 1.0)

#     save_to_folder(i, output, WAV_PATH)

def synthesis(device, model, vocoder, denoiser, text, spk, language, i):
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

    # ── Boost volume ──────────────────────────────────────────────
    # GAIN = 0.5  # try 1.5–4.0; higher = louder (clips if > 1 after scaling)
    GAIN = 0.3  # try 1.5–4.0; higher = louder (clips if > 1 after scaling)
    output["waveform"] = np.clip(output["waveform"] * GAIN, -1.0, 1.0)
    peak = float(np.abs(output["waveform"]).max())
    print(f"[AUDIO] peak amplitude after gain: {peak:.4f}")  # should be close to 1.0
    # ─────────────────────────────────────────────────────────────

    save_to_folder(i, output, WAV_PATH)

def assert_required_models_available():
    save_dir = get_user_data_dir()
    model_path = TTS_MODEL_PATH

    vocoder_path = save_dir / f"{VOCODER_NAME}"
    assert_model_downloaded(vocoder_path, VOCODER_URLS[VOCODER_NAME])
    return {"matcha": model_path, "vocoder": vocoder_path}

if __name__ == "__main__":
    try:
        tts_device = "cuda" if torch.cuda.is_available() else "cpu"
        paths = assert_required_models_available()

        save_dir = get_user_data_dir() 
    
        #tts_model = load_matcha(paths["matcha"], HPARAMS_PATH, tts_device)
        tts_model = load_matcha(paths["matcha"], tts_device)
        vocoder, denoiser = load_vocoder(VOCODER_NAME, paths["vocoder"], tts_device)

        with open(SCRIPT_PATH, 'r') as file:
            
            # greeting
            participantName = input("Enter their name: ")
            synthesis(
                tts_device, tts_model, vocoder, denoiser,
                f"Hi {participantName}, nice to meet you! I'm Pepper!", torch.tensor([7], device=tts_device, dtype=torch.long), LANGUAGE, "greeting"
            )
            q_wav = f"{WAV_PATH}/to_play-greeting.wav"
            wait_done(q_wav)
            moving_on = input("Press enter to continue")


            for i, line in enumerate(file):
                clean_line = line.strip()
                if VOICE == 'chanel':
                    spk = torch.tensor([6], device=tts_device, dtype=torch.long)
                else:
                    print("hmmm wrong voice")
                if VOICE == 'chanel':
                    for emote in emoji_mapping:
                        if emote in clean_line:
                            spk = torch.tensor([emoji_mapping[emote]], device=tts_device, dtype=torch.long)
                            break
                clean_line = re.sub(r"[^\w\s]*[\U00010000-\U0010ffff]+[^\w\s]*", "", clean_line)
                #matcha cannot handle brackets
                clean_line = clean_line.replace(')', '')
                clean_line = clean_line.replace('(', '')
                clean_line = " ".join(clean_line.split())
                print(f"this is the line: {clean_line}")
                if not clean_line:
                    continue
                synthesis(tts_device, tts_model, vocoder, denoiser, clean_line, spk, LANGUAGE, i)

            
            synthesis(
                tts_device, tts_model, vocoder, denoiser,
                "Thank you so much for taking the time to listen to my story!", torch.tensor([7], device=tts_device, dtype=torch.long), LANGUAGE, "final"
            )
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Ctrl+C received — archiving what exists so far...")
# %%
