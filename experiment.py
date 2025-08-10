import threading
import wavio
import tty
import termios

import qi
import sys
import time
import os
import paramiko
from pydub import AudioSegment
from scp import SCPClient

import pyaudio

import whisper
import torch
import numpy as np
from pathlib import Path
import soundfile as sf
import sounddevice as sd
import wave
import random
import requests
import string
import math

pepper_ip = "207.23.199.69"  # Replace with Pepper's IP address
# pepper_ip = "192.168.0.125"

INTRO_PATH = "./intro_files/"
RECORDING_PATH = "./recording/"
TRIAL = "human-affect/"
WAV_PATH = "./outputs"
ASR_MODEL = "small.en"
LLM_MODEL = "llama3.2:1b"
PROMPT = """
            You are welcoming the user.
            Keep the responses short and light and fun.
            Go back and forth 3-5 times with the user then start the experiment by moving towards asking if they are ready to start
            when they are say "Great, let's get started!"
        """
LLM_TEMPERATURE = 0.6

INTO_ANIM_LIST = [
    "Hey_4"
    "Explain_1",
    "Give_6",
    "Explain_10",
    "Please_1"
    "Explain_11",
    "Give_4",
    "Explain_2",
    "Explain_4",
    "ShowTablet_2"
    "Explain_6",
    "Far_2",
    "Explain_2",
    "Give_6",
]
NO_ANIM = ["Bored_1", "Desperate_1", "Desperate_5", "No_8"]
YES_ANIM = ["Happy_4", "Yes_3", "Yes_1"]
NOT_UNDERSTAND_ANIM = ["IDontKnow_1", "IDontKnow_2", "No_2", "No_8"]
TIMING_ANIM = ["YouKnowWhat_1", "YouKnowWhat_5", "Hysterical_1"]
class Authenticator:

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def initialAuthData(self):
        return {'user': self.username, 'token': self.password}

class AuthenticatorFactory:

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def newAuthenticator(self):
        return Authenticator(self.username, self.password)

def run_animation_on_pepper(animation_name = "top"):
    if animation_name == "head_image":
        turn_head([0.0, 80.0])
        # turn_head([80.0, 0.0])
    elif animation_name == "head_front":
        turn_head([80.0, 0.0])
    else:
        # connect to pepper
        animation_name = "top"
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(pepper_ip, username='nao', password='nao')

        command = f"qicli call ALAnimationPlayer.run animations/Stand/{animation_name}'"
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()

def turn_head(angles):
    motion_service  = app.session.service("ALMotion")

    motion_service.setStiffnesses("Head", 1.0)

    # Simple command for the HeadYaw joint at 10% max speed
    names            = "HeadYaw"
    angles           = [math.radians(angle) for angle in angles]
    fractionMaxSpeed = 0.1
    times = [1.0, 2.0]
    motion_service.angleInterpolation(names,angles, times, True)

    time.sleep(3.0)
    motion_service.setStiffnesses("Head", 0.0)

def play_audio_file(ip, file_path, motion = None):
    if motion:
        run_animation_on_pepper(motion)
    audio_player_service = app.session.service("ALAudioPlayer")

    audio_player_service.playFile(file_path) # remote_path)

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
        print("Pepper is listening... Press Space to stop.")

        # Start a thread to wait for a key press
        stop_thread = threading.Thread(target=self.wait_for_stop)
        stop_thread.start()

        # Wait for the recording to stop
        stop_thread.join()

        self.stream.stop()
        self.stream.close()

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
    
def trial_loop(stim_list, stim_path):
    for stim in stim_list:
        play_audio_file(pepper_ip, stim_path + stim, "head_image")
        play_audio_file(pepper_ip, RECORDING_PATH + "/feedback/" + random.choice(feedback_responses), "head_front")
        input(f"Press Enter when you're ready to record 🎙️ ")

        recorder = Recorder()
        recorder.start_recording(RECORDING_PATH + "participant/output.wav")

        result = asr_model.transcribe(RECORDING_PATH + "participant/output.wav")
        result = result['text']
        print(result)

        result = result.translate(str.maketrans('', '', string.punctuation))
        result = result.lower().strip()

        print(f'speaker said: {result}')

        not_understood = True

        # check that they understood
        while not_understood:
            if result != '':
                if result  == "yes":
                    not_understood = False
                    play_audio_file(pepper_ip, RECORDING_PATH + "correct/" + random.choice(correct_responses), None)
                    input(f"Press Enter when you're ready to record 🎙️ ")
                    recorder = Recorder()
                    recorder.start_recording(RECORDING_PATH + "participant/participant_recordings/" + f"correct_{stim}")
                    print("recorded")
                elif result == "no":
                    not_understood = False
                    play_audio_file(pepper_ip, RECORDING_PATH + "incorrect/" + random.choice(incorrect_responses), None)
                    input(f"Press Enter when you're ready to record 🎙️ ")
                    recorder = Recorder()
                    recorder.start_recording(RECORDING_PATH + "participant/participant_recordings/" + f"incorrect_{stim}")
                else:
                    play_audio_file(pepper_ip, RECORDING_PATH + "timing/unknown.wav", None)
                    # get new response
                    input(f"Press Enter when you're ready to record 🎙️ ")
                    # need to add a check where there is no speech for 2 seconds
                    recorder = Recorder()
                    recorder.start_recording(RECORDING_PATH + "output.wav")

                    result = asr_model.transcribe(RECORDING_PATH + "output.wav")
                    result = result['text']

                    result = result.translate(str.maketrans('', '', string.punctuation))
                    result = result.lower().strip()

                    print(f'speaker said: {result}')
                    continue
            else:
                play_audio_file(pepper_ip, RECORDING_PATH + "/incorrect/timing/nothing.wav", None)
                input(f"Press Enter when you're ready to record 🎙️ ")

                recorder = Recorder()
                recorder.start_recording("output.wav")

                result = asr_model.transcribe("output.wav")
                result = result['text']

                print(f'speaker said: {result}')


if __name__ == "__main__":

    app = qi.Application(sys.argv, url="tcps://" + pepper_ip + ":9503")
    logins = ("nao", "nao")
    factory = AuthenticatorFactory(*logins)
    app.session.setClientAuthenticatorFactory(factory)
    app.start()

    p = pyaudio.PyAudio()


    correct_responses = os.listdir(RECORDING_PATH + '/correct/')
    incorrect_responses = os.listdir(RECORDING_PATH + '/incorrect/')
    feedback_responses = os.listdir(RECORDING_PATH + '/feedback/')

    asr_model = whisper.load_model(ASR_MODEL)

    # start by playing the instructions and make sure the understood
    for i, file in enumerate(sorted(os.listdir(INTRO_PATH))):
         play_audio_file(pepper_ip, INTRO_PATH + file, INTO_ANIM_LIST[i])
    
    # practice set
    practice_path = RECORDING_PATH + "stimuli/practice/" + TRIAL
    practice_stim = os.listdir(practice_path)
    random.shuffle(practice_stim)

    trial_loop(practice_stim, practice_path)
    
    play_audio_file(pepper_ip, RECORDING_PATH + "timing/endpractice.wav", None)

    # set blocks
    study_path = RECORDING_PATH + "stimuli/study/" + TRIAL + "/target/"
    study_stim = os.listdir(study_path)
    random.shuffle(study_stim)

    split = int(len(study_stim)/2)
    print(split)
    block_A = study_stim[:split]
    block_B = study_stim[split:]

    trial_loop(block_A, study_path)

    play_audio_file(pepper_ip, RECORDING_PATH + "timing/half.wav", None)

    trial_loop(block_B, study_path)

    play_audio_file(pepper_ip, RECORDING_PATH + "timing/finish.wav", None)