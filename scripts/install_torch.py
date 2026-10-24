"""Install the right PyTorch build for this machine.

PyTorch ships separate wheels per compute backend, and picking the wrong one
is the single most common reason a working GPU sits idle: `pip install torch`
gives you the CPU build on Windows unless you name the CUDA index explicitly.

This script detects the GPU, picks the matching index URL, and installs. It
prints the command before running it, so you can copy it instead if you prefer.

    python scripts/install_torch.py
    python scripts/install_torch.py --cpu       # force the CPU build
    python scripts/install_torch.py --dry-run   # just show the command
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys

#: CUDA runtime version → PyTorch wheel index. Newest first.
CUDA_INDEX = {
    "12.6": "https://download.pytorch.org/whl/cu126",
    "12.4": "https://download.pytorch.org/whl/cu124",
    "12.1": "https://download.pytorch.org/whl/cu121",
    "11.8": "https://download.pytorch.org/whl/cu118",
}
ROCM_INDEX = "https://download.pytorch.org/whl/rocm6.1"
CPU_INDEX = "https://download.pytorch.org/whl/cpu"


def _run(command: list[str], timeout: float = 20.0) -> str | None:
    try:
        proc = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def detect_nvidia() -> tuple[str, str] | None:
    """Return ``(gpu_name, driver_cuda_version)`` when an NVIDIA GPU is present."""
    if not shutil.which("nvidia-smi"):
        return None
    output = _run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"])
    if not output:
        return None
    name = output.strip().splitlines()[0].split(",")[0].strip()

    # `nvidia-smi` prints the maximum CUDA version the driver supports.
    header = _run(["nvidia-smi"]) or ""
    cuda = ""
    for line in header.splitlines():
        if "CUDA Version" in line:
            cuda = line.split("CUDA Version:")[-1].strip().split()[0]
            break
    return name, cuda


def detect_amd() -> str | None:
    if platform.system() != "Linux":
        return None
    if not shutil.which("rocminfo"):
        return None
    return "AMD ROCm"


def choose_index(driver_cuda: str) -> tuple[str, str]:
    """Pick the newest wheel index the driver can run. Returns ``(index, label)``."""
    if not driver_cuda:
        return CUDA_INDEX["12.4"], "CUDA 12.4 (driver version unknown, using a safe default)"
    try:
        major, minor = (int(x) for x in driver_cuda.split(".")[:2])
    except ValueError:
        return CUDA_INDEX["12.4"], "CUDA 12.4 (unparseable driver version)"

    for version, index in CUDA_INDEX.items():
        want_major, want_minor = (int(x) for x in version.split("."))
        # A driver supports every CUDA runtime up to the version it reports.
        if (major, minor) >= (want_major, want_minor):
            return index, f"CUDA {version}"
    return CUDA_INDEX["11.8"], "CUDA 11.8 (oldest supported)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cpu", action="store_true", help="Force the CPU build.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command only.")
    parser.add_argument("--audio", action="store_true", help="Also install torchaudio.")
    args = parser.parse_args(argv)

    print("Detecting the compute backend…\n")

    if args.cpu:
        index, label = CPU_INDEX, "CPU only (forced)"
        gpu_name = "—"
    else:
        nvidia = detect_nvidia()
        if nvidia:
            gpu_name, driver_cuda = nvidia
            index, label = choose_index(driver_cuda)
            print(f"  GPU        {gpu_name}")
            print(f"  Driver     supports CUDA up to {driver_cuda or 'unknown'}")
        elif detect_amd():
            gpu_name, index, label = "AMD (ROCm)", ROCM_INDEX, "ROCm 6.1"
            print(f"  GPU        {gpu_name}")
        elif platform.system() == "Darwin" and platform.machine() == "arm64":
            gpu_name, index, label = "Apple Silicon", "", "Metal (MPS) — the default wheel"
            print(f"  GPU        {gpu_name}")
        else:
            gpu_name, index, label = "none", CPU_INDEX, "CPU only"
            print("  GPU        none detected")

    print(f"  Installing {label}\n")

    packages = ["torch"]
    if args.audio:
        packages.append("torchaudio")

    command = [sys.executable, "-m", "pip", "install", "--upgrade", *packages]
    if index:
        command += ["--index-url", index]

    print("  " + " ".join(command) + "\n")

    if args.dry_run:
        return 0

    result = subprocess.run(command)
    if result.returncode != 0:
        print("\nInstallation failed. Try the command above manually.", file=sys.stderr)
        return result.returncode

    print("\nVerifying…")
    check = subprocess.run(
        [
            sys.executable, "-c",
            "import torch;"
            "print(f'  torch {torch.__version__}');"
            "print(f'  CUDA available: {torch.cuda.is_available()}');"
            "print(f'  device: {torch.cuda.get_device_name(0)}' "
            "if torch.cuda.is_available() else '  running on CPU')",
        ],
    )
    if check.returncode == 0:
        print("\nNext:")
        print('  pip install -e ".[ai]"     # Demucs, Basic Pitch, Whisper')
        print("  retrack doctor             # confirm the model plan changed")
    return check.returncode


if __name__ == "__main__":
    raise SystemExit(main())
