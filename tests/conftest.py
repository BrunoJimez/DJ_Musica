"""Shared fixtures.

Every test runs against synthesised audio with known ground truth. That solves
two problems at once: no copyrighted material in the repository, and assertions
against what is actually true rather than against what we believe is true.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def isolated_home(tmp_path_factory):
    """Keep tests out of the user's real config, cache and library."""
    import os

    home = tmp_path_factory.mktemp("retrack_home")
    os.environ["RETRACK_HOME"] = str(home)

    from retrack.config import reset_settings

    reset_settings()
    return home


@pytest.fixture(scope="session")
def demo_track(tmp_path_factory) -> tuple[Path, dict]:
    """Render the demo track once. Returns ``(wav_path, ground_truth)``."""
    from generate_demo_track import PRESETS, SR, Renderer, _write_wav

    directory = tmp_path_factory.mktemp("demo")
    path = directory / "demo_techhouse.wav"

    renderer = Renderer(PRESETS["techhouse"])
    mix, _buses, truth = renderer.render()
    _write_wav(path, mix, SR)
    (directory / "truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    return path, truth


@pytest.fixture(scope="session")
def demo_dnb(tmp_path_factory) -> tuple[Path, dict]:
    """A 174 BPM track — the case that exposes tempo-octave errors."""
    from generate_demo_track import PRESETS, SR, Renderer, _write_wav

    directory = tmp_path_factory.mktemp("demo_dnb")
    path = directory / "demo_dnb.wav"

    renderer = Renderer(PRESETS["dnb"])
    mix, _buses, truth = renderer.render()
    _write_wav(path, mix, SR)
    return path, truth


@pytest.fixture(scope="session")
def demo_swing(tmp_path_factory) -> tuple[Path, dict]:
    """A track with genuine swing, for the groove tests."""
    from generate_demo_track import PRESETS, SR, Renderer, _write_wav

    directory = tmp_path_factory.mktemp("demo_swing")
    path = directory / "demo_swing.wav"

    renderer = Renderer(PRESETS["house_swing"])
    mix, _buses, truth = renderer.render()
    _write_wav(path, mix, SR)
    return path, truth


@pytest.fixture(scope="session")
def demo_mono(demo_track) -> tuple[np.ndarray, int, dict]:
    """``(mono_samples, sample_rate, truth)`` for the demo track."""
    from retrack.audio.io import load_audio

    path, truth = demo_track
    buffer = load_audio(path, sr=44100, mono=True)
    return buffer.mono(), buffer.sr, truth


@pytest.fixture(scope="session")
def analysis(demo_track):
    """A full analysis of the demo track, computed once for the session."""
    from retrack.analysis import analyze_file

    path, _truth = demo_track
    return analyze_file(path, use_cache=True)


@pytest.fixture
def sine_stereo() -> tuple[np.ndarray, int]:
    """A 1 kHz sine at -23 dBFS — the ITU-R BS.1770 conformance signal."""
    sr = 44100
    amplitude = 10 ** (-23 / 20)
    tone = amplitude * np.sin(2 * np.pi * 1000 * np.arange(sr * 10) / sr)
    return np.stack([tone, tone]).astype(np.float32), sr
