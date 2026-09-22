#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# One-shot setup for the BB_pepper-experiment stack inside WSL2 / Ubuntu.
#
# Recreates the old Linux `bbpepper` conda env on a fresh Ubuntu WSL install:
#   - system build deps (portaudio, libsndfile, ffmpeg, cmake for pyopenjtalk)
#   - Miniconda + a `bbpepper` env on Python 3.11
#   - the pinned deps from the ORIGINAL requirements.txt (Linux pip freeze),
#     with only the 9 unusable "pkg @ file:///home/conda/..." references
#     stripped to bare names so pip can resolve them -- every real version
#     pin (incl. av==11.0.0) is left exactly as it was
#   - the vendored Matcha-TTS as an editable install (NOT the broken PyPI one)
#   - qi (the NAOqi SDK) -- Linux-only wheels, which is the whole reason for WSL
#
# Safe to re-run. Robot / TTS / Whisper / LLM code all target this one env.
# ---------------------------------------------------------------------------
set -uo pipefail

REPO_URL="https://github.com/rosielab/BB_pepper-experiment.git"
BRANCH="pilot-setup"
DEST="$HOME/BB_pepper-experiment"
OLD_WIN_DIR="/mnt/c/Users/pujas/Desktop/BB_pepper-experiment"
ENV_NAME="bbpepper"
PY_VERSION="3.11"

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!!  %s\033[0m\n' "$*"; }

# --- 1. sanity: must be inside WSL / Linux ----------------------------------
if ! grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  warn "This doesn't look like WSL. Run it from the Ubuntu shell, not PowerShell."
  exit 1
fi

# --- 2. system packages ---------------------------------------------------
log "Installing system build dependencies (sudo password may be asked)"
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  build-essential cmake pkg-config git curl ca-certificates \
  portaudio19-dev libsndfile1 libasound2-dev libasound2-plugins alsa-utils ffmpeg \
  libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
  libavfilter-dev libswscale-dev libswresample-dev \
  espeak-ng \
  python3-dev
# espeak-ng: phonemizer backend for Matcha-TTS text cleaning
# libasound2-plugins: ALSA->PulseAudio bridge so arecord works under WSLg
# ^ libav*-dev: needed to build av==11.0.0 from source (no cp311 wheel on PyPI)

# --- 3. Miniconda -------------------------------------------------------
CONDA_DIR="$HOME/miniconda3"
if [ ! -x "$CONDA_DIR/bin/conda" ]; then
  log "Installing Miniconda to $CONDA_DIR"
  curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh
  bash /tmp/miniconda.sh -b -p "$CONDA_DIR"
  rm -f /tmp/miniconda.sh
  "$CONDA_DIR/bin/conda" init bash
else
  log "Miniconda already present at $CONDA_DIR"
fi

# make `conda` usable in this non-interactive shell
source "$CONDA_DIR/etc/profile.d/conda.sh"
# accept channel ToS non-interactively (newer conda prompts otherwise)
conda tos accept --override-channels \
  --channel https://repo.anaconda.com/pkgs/main \
  --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true

# --- 4. clone the repo (into the Linux fs, not /mnt/c) ---------------------
if [ ! -d "$DEST/.git" ]; then
  log "Cloning $REPO_URL ($BRANCH) into $DEST"
  if ! git clone -b "$BRANCH" "$REPO_URL" "$DEST"; then
    warn "Clone failed (private repo?). Authenticate with 'gh auth login' or a PAT, then re-run."
    exit 1
  fi
else
  log "Repo already cloned at $DEST"
fi
cd "$DEST"

# --- 5. conda env ------------------------------------------------------
if ! conda env list | grep -qE "^\s*${ENV_NAME}\s"; then
  log "Creating conda env '$ENV_NAME' (Python $PY_VERSION)"
  conda create -n "$ENV_NAME" "python=$PY_VERSION" -y
else
  log "Conda env '$ENV_NAME' already exists"
fi
conda activate "$ENV_NAME"
# NB: keep setuptools <81 -- lightning==2.1.3 (and other old pins) still call
# pkg_resources.declare_namespace(), which newer setuptools has removed.
python -m pip install --upgrade pip wheel
python -m pip install --upgrade 'setuptools<81'

# --- 6. python deps ---------------------------------------------------
REQ_SRC=""
[ -f "$DEST/requirements.txt" ] && REQ_SRC="$DEST/requirements.txt"
[ -z "$REQ_SRC" ] && [ -f "$OLD_WIN_DIR/requirements.txt" ] && REQ_SRC="$OLD_WIN_DIR/requirements.txt"

if [ -n "$REQ_SRC" ]; then
  log "Installing pinned deps from $REQ_SRC  (--no-deps: exact reproduction)"
  # 1) drop the vendored-locally matcha-tts (installed editable in step 7)
  # 2) rewrite "pkg @ file:///home/conda/.../work" -> "pkg" (paths don't exist
  #    off the conda-forge build servers)
  grep -viE '^matcha-tts==' "$REQ_SRC" \
    | sed -E 's/^([A-Za-z0-9_.-]+) @ file:\/\/.*$/\1/' \
    > /tmp/req_bbpepper.txt
  echo "  (rewrote $(grep -cE '^[A-Za-z0-9_.-]+$' /tmp/req_bbpepper.txt) conda-path refs to bare names)"
  # requirements.txt is a full pip freeze -- every transitive dep is already
  # pinned in it. It also contains version pairs a modern resolver rejects
  # (e.g. MarkupSafe 3 vs gradio 3.43, tokenizers 0.22 vs faster-whisper 1.0.1)
  # that only coexisted because the original env was built incrementally.
  # --no-deps installs each pin verbatim and skips resolution, reproducing the
  # old env exactly. `pip check` will note the latent mismatches -- harmless
  # unless that specific code path runs.
  pip install --no-deps -r /tmp/req_bbpepper.txt \
    || warn "A pinned package failed to build -- see log; comment it out or get it from conda-forge, then re-run."
else
  warn "requirements.txt not found in repo or old Windows folder -- skipping bulk install."
fi

# --- 7. vendored Matcha-TTS (editable, no deps: they're covered above) ----
if [ -d "$DEST/Matcha-TTS" ]; then
  log "Installing vendored Matcha-TTS as editable (--no-deps)"
  pip install -e "$DEST/Matcha-TTS" --no-deps --no-build-isolation \
    || warn "Matcha-TTS editable install failed -- check the Cython build (needs build-essential)."
fi

# --- 8. NAOqi SDK ---------------------------------------------------
log "Installing qi (NAOqi SDK -- Linux-only, the reason we're in WSL)"
pip install qi || warn "pip install qi failed. Try: pip install qi==3.1.5  (or check https://pypi.org/project/qi/)"

# --- 9. checkpoints not in git (hand-carry from the old folder) -----------
log "Copying git-ignored voice checkpoints from the old Windows folder"
for sub in storytelling-llm_experiment storytelling-pilot; do
  if [ -d "$OLD_WIN_DIR/$sub" ] && [ -d "$DEST/$sub" ]; then
    shopt -s nullglob
    for f in "$OLD_WIN_DIR/$sub"/*.ckpt "$OLD_WIN_DIR/$sub"/*.pt; do
      base="$(basename "$f")"
      if [ ! -f "$DEST/$sub/$base" ]; then
        echo "  + $sub/$base"
        cp -n "$f" "$DEST/$sub/$base"
      fi
    done
    shopt -u nullglob
  fi
done

# --- 10. smoke test --------------------------------------------------
log "Smoke test"
python - <<'PY'
mods = ["torch", "qi", "whisper", "matcha", "sounddevice", "soundfile",
        "pyaudio", "paramiko", "scp", "pydub", "openai", "tiktoken", "emoji"]
ok, bad = [], []
for m in mods:
    try:
        __import__(m); ok.append(m)
    except Exception as e:
        bad.append(f"{m}: {e.__class__.__name__}: {e}")
print("  imported OK :", ", ".join(ok) or "(none)")
if bad:
    print("  FAILED      :")
    for b in bad: print("    -", b)
try:
    import torch
    print(f"  torch {torch.__version__} | CUDA available: {torch.cuda.is_available()}"
          + (f" | {torch.cuda.get_device_name(0)}" if torch.cuda.is_available() else ""))
except Exception as e:
    print("  torch check failed:", e)
PY

cat <<EOF

------------------------------------------------------------------
Done. From now on, in the Ubuntu shell:

    conda activate $ENV_NAME
    cd $DEST/storytelling-llm_experiment
    python pilot.py            # or storytelling.py / experiment.py

Notes:
  * Audio in/out (sounddevice, pyaudio) runs through WSLg's PulseAudio.
  * Outbound connections to Pepper (NAOqi 9559, SSH/SCP) work over WSL2's
    default NAT. If the robot needs to reach the laptop, enable mirrored
    networking in %USERPROFILE%\\.wslconfig:  [wsl2]\\nnetworkingMode=mirrored
  * If 'import qi' failed, the robot scripts won't connect -- that package
    is the one hard requirement that forced this WSL setup.
------------------------------------------------------------------
EOF
