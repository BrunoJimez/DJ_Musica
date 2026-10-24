"""Measure the feature vectors of reference drum sounds.

The drum classifier in ``retrack.analysis.drums`` matches each detected hit
against a set of prototype feature vectors. Those prototypes have to be
*measured*, not guessed: a hand-written guess at "where a kick's spectral
centroid sits" is wrong by enough to make the classifier label every kick in a
four-on-the-floor track as a tom.

This script synthesises reference hits with the same generators the demo
track uses, runs them through the real feature extractor, and prints a
ready-to-paste ``_PROTOTYPES`` table. Re-run it whenever the feature set in
``hit_features`` changes.

    python tools/calibrate_drum_prototypes.py
    python tools/calibrate_drum_prototypes.py --samples path/to/one_shots/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

from retrack.analysis.drums import hit_features  # noqa: E402

SR = 44100

FEATURE_NAMES = (
    "centroid", "e<120", "e120-1k", "e1-5k", "e>5k", "flatness", "decay", "attack", "peak",
)


def _reference_sounds() -> dict[str, np.ndarray]:
    """Synthesised one-shots covering the classes the matcher knows about."""
    from generate_demo_track import (
        clap,
        hat,
        kick,
        noise,
        onepole_hp,
        ride,
        sine,
        snare,
    )

    def tom(freq: float, decay: float) -> np.ndarray:
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        pitch = freq * (1.0 + 0.35 * np.exp(-t / 0.05))
        phase = 2 * np.pi * np.cumsum(pitch) / SR
        body = np.sin(phase) * np.exp(-t / decay)
        return (body * 0.8 + noise(n, 7) * np.exp(-t / 0.004) * 0.15).astype(np.float32)

    def crash() -> np.ndarray:
        n = int(1.2 * SR)
        t = np.arange(n) / SR
        body = onepole_hp(noise(n, 21), SR, 2500)
        for ratio in (1.0, 1.41, 1.78, 2.31, 3.07):
            body += sine(ratio * 700, n, SR) * 0.08
        return (body * np.exp(-t / 0.55) * 0.5).astype(np.float32)

    def shaker() -> np.ndarray:
        n = int(0.10 * SR)
        t = np.arange(n) / SR
        return (onepole_hp(noise(n, 31), SR, 7000) * np.exp(-t / 0.020) * 0.4).astype(np.float32)

    def rimshot() -> np.ndarray:
        n = int(0.09 * SR)
        t = np.arange(n) / SR
        tone = (sine(420, n, SR) + sine(780, n, SR) * 0.7) * np.exp(-t / 0.010)
        return (tone * 0.6 + onepole_hp(noise(n, 41), SR, 2000) * np.exp(-t / 0.006)).astype(
            np.float32
        )

    return {
        "kick": kick(SR),
        "snare": snare(SR),
        "clap": clap(SR),
        "rimshot": rimshot(),
        "closed_hat": hat(SR),
        "open_hat": hat(SR, open_hat=True),
        "ride": ride(SR),
        "crash": crash(),
        "low_tom": tom(90.0, 0.30),
        "mid_tom": tom(160.0, 0.24),
        "shaker": shaker(),
    }


def _load_samples(folder: Path) -> dict[str, np.ndarray]:
    """Load user one-shots. File names must start with a known class name."""
    import soundfile as sf

    known = set(_reference_sounds())
    grouped: dict[str, list[np.ndarray]] = {}
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in (".wav", ".flac", ".aiff", ".aif"):
            continue
        stem = path.stem.lower()
        match = next((k for k in known if stem.startswith(k)), None)
        if match is None:
            continue
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        mono = data.mean(axis=1)
        if sr != SR:
            from retrack.audio.io import _resample

            mono = _resample(mono[None, :], sr, SR)[0]
        grouped.setdefault(match, []).append(mono)

    return {
        name: np.stack([_pad(s, max(len(x) for x in samples)) for s in samples]).mean(axis=0)
        for name, samples in grouped.items()
    }


def _pad(x: np.ndarray, length: int) -> np.ndarray:
    return x[:length] if x.size >= length else np.pad(x, (0, length - x.size))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--samples", type=Path, default=None)
    parser.add_argument("--weights", action="store_true", help="also suggest feature weights")
    args = parser.parse_args(argv)

    sounds = _reference_sounds()
    if args.samples:
        loaded = _load_samples(args.samples)
        print(f"loaded {len(loaded)} classes from {args.samples}\n")
        sounds.update(loaded)

    print(f"{'class':<12}" + "".join(f"{n:>9}" for n in FEATURE_NAMES))
    print("-" * (12 + 9 * len(FEATURE_NAMES)))

    vectors: dict[str, np.ndarray] = {}
    for name, sound in sounds.items():
        # Pad so the tail window has something to measure.
        padded = np.pad(sound, (0, SR // 2))
        features = hit_features(padded, SR, np.array([0.0]))[0]
        vectors[name] = features
        print(f"{name:<12}" + "".join(f"{v:>9.3f}" for v in features))

    print("\n# Paste into retrack/analysis/drums.py")
    print("_PROTOTYPES = {")
    print("    #" + " " * 12 + "  ".join(f"{n:>6}" for n in FEATURE_NAMES))
    for name, features in vectors.items():
        values = ", ".join(f"{v:.3f}" for v in features)
        print(f'    "{name}": (({values}),')
        print(f'{" " * (len(name) + 8)}(1.0,) * 9),')
    print("}")

    if args.weights:
        matrix = np.stack(list(vectors.values()))
        spread = matrix.std(axis=0)
        # A feature that separates the classes well deserves more weight.
        weights = spread / max(spread.mean(), 1e-9)
        print("\n# suggested per-feature weights (by between-class spread)")
        print("WEIGHTS = (" + ", ".join(f"{w:.2f}" for w in weights) + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
