import subprocess
import re
import time
import torch
import whisper
import os
from joblib import dump, load
import argparse

import subprocess
import re
import time
import torch
import whisper
import os
from joblib import dump, load
import argparse


def transcribe_audio(model, audio_path: str):
    """Transcribe audio using Whisper and log time taken."""
    print("Starting transcription...")
    start_time = time.time()
    result = model.transcribe(audio_path)
    end_time = time.time()
    transcription_time = end_time - start_time
    return result["text"], transcription_time

def record_audio(output_path: str, device: str, duration: int = 5):
    """Record audio using arecord with a timeout."""
    print(f"Recording audio for {duration} seconds...")
    rec_cmd = [
        "arecord",
        "-D", device,
        "-f", "S16_LE",
        "-r", "16000",
        "-c", "1",
        output_path
    ]
    try:
        # Use subprocess.Popen to control the process
        process = subprocess.Popen(rec_cmd)
        time.sleep(duration)  # Wait for the specified duration
        process.terminate()  # Terminate the process after the duration
        process.wait()  # Ensure the process has exited
        print(f"Audio recorded and saved to {output_path}")
    except Exception as e:
        print(f"Error during recording: {e}")
        if process:
            process.terminate()

def find_alsa_device(card_name: str) -> str:
    """Find ALSA device string by card name substring."""
    result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if card_name in line:
            match = re.search(r"card (\d+):.*device (\d+):", line)
            if match:
                card, device = match.groups()
                return f"plughw:{card},{device}"
    raise RuntimeError(f"ALSA device '{card_name}' not found")

def load_cached_model(model_name="medium.en", cache_path="./whisper_model_cache.joblib", use_gpu=True):
    """Load Whisper model from cache or initialize and cache it."""
    if os.path.exists(cache_path):
        print("Loading Whisper model from cache...")
        model = load(cache_path)
    else:
        print("Loading Whisper model for the first time...")
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        model = whisper.load_model(model_name, device=device)
        dump(model, cache_path)
        print("Model cached for future use.")
    return model

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Whisper transcription script with GPU toggle.")
    parser.add_argument("--use-gpu", action="store_true", help="Enable GPU for Whisper (if available).")
    args = parser.parse_args()

    try:
        # Find DJI MIC MINI device
        try:
            device = find_alsa_device("DJI MIC MINI")
        except RuntimeError:
            device = "plughw:2,0"  # fallback default
            print("Warning: DJI MIC MINI not found, using hardcoded fallback")

        # Record audio
        output_path = "./test_audio.wav"
        record_audio(output_path, device)

        # Load Whisper model
        print("Loading Whisper model...")
        model = load_cached_model("medium.en", use_gpu=args.use_gpu)

        # Check if GPU is available and being used
        device_type = "GPU" if args.use_gpu and torch.cuda.is_available() else "CPU"
        print(f"Whisper is using: {device_type}")

        # Transcribe audio
        transcription, transcription_time = transcribe_audio(model, output_path)

        # Log results
        print("\n--- Transcription Results ---")
        print(f"Transcription: {transcription}")
        print(f"Time taken: {transcription_time:.2f} seconds")
        print(f"Device used: {device_type}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

def find_alsa_device(card_name: str) -> str:
    """Find ALSA device string by card name substring."""
    result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if card_name in line:
            match = re.search(r"card (\d+):.*device (\d+):", line)
            if match:
                card, device = match.groups()
                return f"plughw:{card},{device}"
    raise RuntimeError(f"ALSA device '{card_name}' not found")

def load_cached_model(model_name="medium.en", cache_path="./whisper_model_cache.joblib", use_gpu=True):
    """Load Whisper model from cache or initialize and cache it."""
    if os.path.exists(cache_path):
        print("Loading Whisper model from cache...")
        model = load(cache_path)
    else:
        print("Loading Whisper model for the first time...")
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        model = whisper.load_model(model_name, device=device)
        dump(model, cache_path)
        print("Model cached for future use.")
    return model

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Whisper transcription script with GPU toggle.")
    parser.add_argument("--use-gpu", action="store_true", help="Enable GPU for Whisper (if available).")
    args = parser.parse_args()

    try:
        # Find DJI MIC MINI device
        try:
            device = find_alsa_device("DJI MIC MINI")
        except RuntimeError:
            device = "plughw:2,0"  # fallback default
            print("Warning: DJI MIC MINI not found, using hardcoded fallback")

        # Record audio
        output_path = "./test_audio.wav"
        record_audio(output_path, device)

        # Load Whisper model
        print("Loading Whisper model...")
        model = load_cached_model("medium.en", use_gpu=args.use_gpu)

        # Check if GPU is available and being used
        device_type = "GPU" if args.use_gpu and torch.cuda.is_available() else "CPU"
        print(f"Whisper is using: {device_type}")

        # Transcribe audio
        transcription, transcription_time = transcribe_audio(model, output_path)

        # Log results
        print("\n--- Transcription Results ---")
        print(f"Transcription: {transcription}")
        print(f"Time taken: {transcription_time:.2f} seconds")
        print(f"Device used: {device_type}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()