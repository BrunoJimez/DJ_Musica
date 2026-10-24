#!/usr/bin/env bash
# RETRACK Studio setup for macOS and Linux.
#
#   ./scripts/setup.sh                    # gui, live, reports
#   ./scripts/setup.sh --full             # everything
#   ./scripts/setup.sh --extras gui,live  # pick your own
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EXTRAS="gui,live,reports"
SKIP_TORCH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full)   EXTRAS="gui,live,reports,ai,plugins,mir,llm"; shift ;;
    --extras) EXTRAS="$2"; shift 2 ;;
    --skip-torch) SKIP_TORCH=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

step() { printf '\n\033[36m=== %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32mOK\033[0m  %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m   %s\n' "$1"; }

echo "RETRACK Studio — setup"

# ---------------------------------------------------------------------------
step "Finding a supported Python"

# librosa depends on numba, which lags each new Python release by months.
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    major="${version%%.*}"; minor="${version##*.}"
    if [[ "$major" -eq 3 && "$minor" -ge 10 && "$minor" -le 13 ]]; then
      PYTHON="$candidate"
      ok "$candidate (Python $version)"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "No Python 3.10-3.13 found. Install 3.11 or 3.12." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
step "System libraries"

if [[ "$(uname)" == "Darwin" ]]; then
  if command -v brew >/dev/null 2>&1; then
    brew list ffmpeg    >/dev/null 2>&1 || brew install ffmpeg
    brew list libsndfile >/dev/null 2>&1 || brew install libsndfile
    brew list portaudio  >/dev/null 2>&1 || brew install portaudio
    ok "ffmpeg, libsndfile, portaudio"
  else
    warn "Homebrew not found — install ffmpeg, libsndfile and portaudio manually"
  fi
elif command -v apt-get >/dev/null 2>&1; then
  warn "installing system packages (sudo required)"
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 portaudio19-dev libegl1 libgl1 libxkbcommon-x11-0
  ok "system libraries installed"
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y ffmpeg libsndfile portaudio-devel
  ok "system libraries installed"
else
  warn "unknown package manager — install ffmpeg, libsndfile and portaudio yourself"
fi

# ---------------------------------------------------------------------------
step "Creating the virtual environment"

if [[ -d .venv ]]; then
  ok ".venv already exists, reusing it"
else
  "$PYTHON" -m venv .venv
  ok "created .venv"
fi
VENV_PY=".venv/bin/python"

# ---------------------------------------------------------------------------
step "Installing RETRACK"

"$VENV_PY" -m pip install --upgrade pip --quiet
echo "  extras: $EXTRAS"
"$VENV_PY" -m pip install -e ".[$EXTRAS]"
ok "RETRACK installed"

# ---------------------------------------------------------------------------
if [[ "$SKIP_TORCH" -eq 0 ]]; then
  step "GPU acceleration"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name --format=csv,noheader | sed 's/^/  found: /'
    read -r -p "  Install the CUDA build of PyTorch? [Y/n] " answer
    if [[ "$answer" != "n" && "$answer" != "N" ]]; then
      "$VENV_PY" scripts/install_torch.py
      "$VENV_PY" -m pip install -e ".[ai]"
      ok "GPU stack installed"
    fi
  elif [[ "$(uname -m)" == "arm64" && "$(uname)" == "Darwin" ]]; then
    read -r -p "  Apple Silicon detected. Install PyTorch with Metal support? [Y/n] " answer
    if [[ "$answer" != "n" && "$answer" != "N" ]]; then
      "$VENV_PY" -m pip install torch
      "$VENV_PY" -m pip install -e ".[ai]"
      ok "Metal stack installed"
    fi
  else
    warn "no supported GPU detected — everything runs on CPU"
  fi
fi

# ---------------------------------------------------------------------------
step "Generating the demo track"
"$VENV_PY" examples/generate_demo_track.py
ok "demo rendered to examples/generated/"

step "System check"
"$VENV_PY" -m retrack doctor

printf '\n\033[32m=== Ready\033[0m\n'
cat <<'EOF'

Activate the environment:
    source .venv/bin/activate

Then try:
    retrack gui
    retrack analyze examples/generated/retrack_demo_techhouse.wav
    retrack report  examples/generated/retrack_demo_techhouse.wav --out reports

EOF
