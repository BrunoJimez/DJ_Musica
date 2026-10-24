"""Synthesise a royalty-free demo track with known ground truth.

Why this exists
---------------
Testing a music-analysis program requires music. Committing real tracks to a
public repository is a copyright problem, and testing against material whose
"true" BPM and key you only *believe* you know is not testing at all.

So RETRACK ships a generator instead. Every parameter — tempo, key, chord
progression, arrangement, drum pattern, swing — is written down here, which
means the test suite can assert against exact ground truth, and anyone
cloning the repo can produce a demo file with no downloads.

The output is a complete 128 BPM A-minor tech-house arrangement: intro, build,
drop, breakdown, second drop, outro, with a four-on-the-floor kit, a
sidechained bass, a plucked chord stab, an arp and a pad.

Usage
-----
    python examples/generate_demo_track.py                     # default track
    python examples/generate_demo_track.py --bpm 140 --key F#m --out other.wav
    python examples/generate_demo_track.py --list-presets
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SR = 44100
PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_ALIASES = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def note_to_midi(name: str, octave: int = 4) -> int:
    name = _ALIASES.get(name, name)
    return PITCH_CLASSES.index(name) + (octave + 1) * 12


def midi_to_hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# ---------------------------------------------------------------------------
# Envelopes and oscillators
# ---------------------------------------------------------------------------


def adsr(n: int, sr: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    """Linear-attack, exponential-decay ADSR of exactly *n* samples."""
    env = np.zeros(n, dtype=np.float32)
    a_n = max(1, int(a * sr))
    d_n = max(1, int(d * sr))
    r_n = max(1, int(r * sr))
    sustain_n = max(0, n - a_n - d_n - r_n)

    idx = 0
    env[idx : idx + a_n] = np.linspace(0.0, 1.0, a_n, dtype=np.float32)
    idx += a_n
    if idx < n:
        take = min(d_n, n - idx)
        env[idx : idx + take] = (1.0 - (1.0 - s) * (1 - np.exp(-4 * np.linspace(0, 1, take))))[
            :take
        ]
        idx += take
    if idx < n and sustain_n > 0:
        take = min(sustain_n, n - idx)
        env[idx : idx + take] = s
        idx += take
    if idx < n:
        take = n - idx
        env[idx:] = s * np.exp(-5.0 * np.linspace(0, 1, take, dtype=np.float32))
    return env


def saw(freq: float, n: int, sr: int, *, detune_cents: float = 0.0, voices: int = 1) -> np.ndarray:
    """Band-limited-ish supersaw via additive synthesis (no aliasing below Nyquist)."""
    t = np.arange(n, dtype=np.float64) / sr
    out = np.zeros(n, dtype=np.float64)
    for v in range(voices):
        offset = 0.0 if voices == 1 else (v - (voices - 1) / 2) * detune_cents / (voices or 1)
        f = freq * 2.0 ** (offset / 1200.0)
        harmonics = int(min(60, (sr / 2) / max(f, 1.0)))
        phase = np.random.default_rng(v + int(f)).uniform(0, 2 * np.pi)
        for h in range(1, harmonics + 1):
            out += (1.0 / h) * np.sin(2 * np.pi * f * h * t + phase)
    return (out / max(voices, 1) * 0.3).astype(np.float32)


def square(freq: float, n: int, sr: int, duty: float = 0.5) -> np.ndarray:
    t = np.arange(n, dtype=np.float64) / sr
    out = np.zeros(n, dtype=np.float64)
    harmonics = int(min(40, (sr / 2) / max(freq, 1.0)))
    for h in range(1, harmonics + 1, 2):
        out += (1.0 / h) * np.sin(2 * np.pi * freq * h * t)
    return (out * 0.35 * (1.0 if duty == 0.5 else 0.8)).astype(np.float32)


def sine(freq: float, n: int, sr: int) -> np.ndarray:
    t = np.arange(n, dtype=np.float64) / sr
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def noise(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32) * 0.3


def onepole_lp(x: np.ndarray, sr: int, cutoff: float | np.ndarray) -> np.ndarray:
    """One-pole low-pass that accepts a time-varying cutoff (for filter sweeps)."""
    cutoff_arr = np.full(x.size, cutoff, dtype=np.float64) if np.isscalar(cutoff) else np.asarray(
        cutoff, dtype=np.float64
    )
    coef = np.exp(-2.0 * np.pi * np.clip(cutoff_arr, 20, sr / 2 - 100) / sr)
    out = np.empty_like(x, dtype=np.float32)
    prev = 0.0
    for i in range(x.size):
        prev = (1.0 - coef[i]) * x[i] + coef[i] * prev
        out[i] = prev
    return out


def onepole_hp(x: np.ndarray, sr: int, cutoff: float) -> np.ndarray:
    return (x - onepole_lp(x, sr, cutoff)).astype(np.float32)


# ---------------------------------------------------------------------------
# Drum synthesis
# ---------------------------------------------------------------------------


def kick(sr: int = SR, length: float = 0.42) -> np.ndarray:
    n = int(length * sr)
    t = np.arange(n) / sr
    # Pitch envelope: 120 Hz -> 45 Hz over 60 ms. This is the classic 909 sweep.
    freq = 45.0 + 75.0 * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase) * np.exp(-t / 0.16)
    click = noise(n, 1) * np.exp(-t / 0.004) * 0.6
    return np.tanh((body + click) * 1.6).astype(np.float32) * 0.9


def snare(sr: int = SR, length: float = 0.24) -> np.ndarray:
    n = int(length * sr)
    t = np.arange(n) / sr
    tone = (sine(185, n, sr) + sine(330, n, sr) * 0.6) * np.exp(-t / 0.03)
    rattle = onepole_hp(noise(n, 2), sr, 1200) * np.exp(-t / 0.085)
    return np.tanh((tone * 0.5 + rattle * 1.1) * 1.2).astype(np.float32) * 0.6


def clap(sr: int = SR, length: float = 0.30) -> np.ndarray:
    n = int(length * sr)
    t = np.arange(n) / sr
    out = np.zeros(n, dtype=np.float32)
    # Three fast repeats + a tail: what makes a clap sound like hands.
    for i, delay in enumerate((0.0, 0.010, 0.021)):
        start = int(delay * sr)
        seg = onepole_hp(noise(n - start, 3 + i), sr, 900) * np.exp(
            -np.arange(n - start) / sr / 0.012
        )
        out[start:] += seg * (0.9 - i * 0.15)
    out += onepole_hp(noise(n, 9), sr, 1100) * np.exp(-t / 0.12) * 0.5
    return (out * 0.5).astype(np.float32)


def hat(sr: int = SR, length: float = 0.06, open_hat: bool = False) -> np.ndarray:
    n = int((0.28 if open_hat else length) * sr)
    t = np.arange(n) / sr
    metallic = np.zeros(n, dtype=np.float32)
    # Six inharmonic square partials — the 808/909 hat recipe.
    for ratio in (2.0, 3.0, 4.16, 5.43, 6.79, 8.21):
        metallic += square(ratio * 320.0, n, sr) * 0.2
    decay = 0.09 if open_hat else 0.018
    return (onepole_hp(metallic, sr, 6500) * np.exp(-t / decay) * 0.35).astype(np.float32)


def ride(sr: int = SR, length: float = 0.5) -> np.ndarray:
    n = int(length * sr)
    t = np.arange(n) / sr
    body = onepole_hp(noise(n, 11), sr, 3000)
    for ratio in (1.0, 1.5, 2.3):
        body += sine(ratio * 900, n, sr) * 0.15
    return (body * np.exp(-t / 0.22) * 0.22).astype(np.float32)


# ---------------------------------------------------------------------------
# Track definition
# ---------------------------------------------------------------------------


@dataclass
class SectionSpec:
    label: str
    bars: int
    #: Which layers play. Names must match the synth functions below.
    layers: tuple[str, ...]
    #: Multiplier applied to the whole section.
    gain: float = 1.0
    #: A rising low-pass sweep, given as (start_hz, end_hz), or None.
    sweep: tuple[float, float] | None = None


@dataclass
class TrackSpec:
    name: str = "RETRACK Demo — Neon Grid"
    bpm: float = 128.0
    key_root: str = "A"
    key_mode: str = "minor"
    beats_per_bar: int = 4
    swing: float = 0.5
    #: Scale degrees of the four-chord loop, as semitone offsets from the root.
    progression: tuple[int, ...] = (0, 5, 3, 7)  # i - iv - VI - v  in A minor
    chord_quality: tuple[str, ...] = ("min", "min", "maj", "min")
    sections: tuple[SectionSpec, ...] = field(
        default_factory=lambda: (
            SectionSpec("intro", 8, ("hat", "pad"), 0.55),
            SectionSpec("build", 8, ("kick", "hat", "pad", "arp"), 0.75, sweep=(300, 9000)),
            SectionSpec("drop", 16, ("kick", "clap", "hat", "openhat", "bass", "stab", "arp")),
            SectionSpec("breakdown", 8, ("pad", "stab", "ride"), 0.6),
            SectionSpec("build2", 8, ("kick", "hat", "pad", "arp", "snare_roll"), 0.8,
                        sweep=(500, 12000)),
            SectionSpec("drop2", 16, ("kick", "clap", "hat", "openhat", "bass", "stab", "arp")),
            SectionSpec("outro", 8, ("kick", "hat", "pad"), 0.5),
        )
    )
    seed: int = 20260730


PRESETS: dict[str, TrackSpec] = {
    "techhouse": TrackSpec(),
    "techno": TrackSpec(
        name="RETRACK Demo — Iron Cellar",
        bpm=140.0,
        key_root="F",
        key_mode="minor",
        progression=(0, 0, 10, 8),
        chord_quality=("min", "min", "maj", "maj"),
    ),
    "house_swing": TrackSpec(
        name="RETRACK Demo — Shuffle Room",
        bpm=124.0,
        key_root="C",
        key_mode="minor",
        swing=0.62,
        progression=(0, 3, 8, 5),
        chord_quality=("min", "maj", "maj", "min"),
    ),
    "dnb": TrackSpec(
        name="RETRACK Demo — Halfstep",
        bpm=174.0,
        key_root="D",
        key_mode="minor",
        progression=(0, 7, 5, 3),
        chord_quality=("min", "min", "min", "maj"),
    ),
}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class Renderer:
    def __init__(self, spec: TrackSpec, sr: int = SR) -> None:
        self.spec = spec
        self.sr = sr
        self.beat = 60.0 / spec.bpm
        self.bar = self.beat * spec.beats_per_bar
        self.total_bars = sum(s.bars for s in spec.sections)
        self.duration = self.total_bars * self.bar + 2.0
        self.n = int(self.duration * sr)
        self.rng = np.random.default_rng(spec.seed)
        self.root_midi = note_to_midi(spec.key_root, 3)
        # Per-stem buses, so the generator can also emit ground-truth stems.
        self.buses: dict[str, np.ndarray] = {
            name: np.zeros(self.n, dtype=np.float32)
            for name in ("drums", "bass", "chords", "lead", "pad")
        }
        self.events: list[dict] = []

    # -- helpers -----------------------------------------------------------
    def _place(self, bus: str, sample: np.ndarray, at: float, gain: float = 1.0) -> None:
        start = int(at * self.sr)
        if start < 0 or start >= self.n:
            return
        end = min(self.n, start + sample.size)
        self.buses[bus][start:end] += sample[: end - start] * gain

    def _swing_offset(self, step: int) -> float:
        """Delay odd 8th notes to create swing."""
        if self.spec.swing <= 0.5 or step % 2 == 0:
            return 0.0
        return (self.spec.swing - 0.5) * self.beat

    def _chord_midi(self, bar_index: int) -> list[int]:
        idx = bar_index % len(self.spec.progression)
        root = self.root_midi + self.spec.progression[idx]
        quality = self.spec.chord_quality[idx]
        third = 3 if quality == "min" else 4
        return [root, root + third, root + 7, root + 12]

    # -- layers ------------------------------------------------------------
    def _render_section(self, section: SectionSpec, bar_offset: int) -> None:
        spec = self.spec
        for local_bar in range(section.bars):
            bar_index = bar_offset + local_bar
            bar_time = bar_index * self.bar
            chord = self._chord_midi(bar_index)
            layers = section.layers
            gain = section.gain

            # ---- drums ---------------------------------------------------
            if "kick" in layers:
                for beat in range(spec.beats_per_bar):
                    t = bar_time + beat * self.beat
                    self._place("drums", kick(self.sr), t, 1.0 * gain)
                    self.events.append({"t": round(t, 5), "kind": "kick"})
            if "clap" in layers:
                for beat in (1, 3):
                    t = bar_time + beat * self.beat
                    self._place("drums", clap(self.sr), t, 0.9 * gain)
                    self.events.append({"t": round(t, 5), "kind": "clap"})
            if "snare_roll" in layers and local_bar >= section.bars - 2:
                # Accelerating roll into the drop: 8ths, then 16ths, then 32nds.
                division = 2 if local_bar == section.bars - 2 else 4
                for step in range(spec.beats_per_bar * division):
                    t = bar_time + step * self.beat / division
                    ramp = 0.35 + 0.65 * (step / (spec.beats_per_bar * division))
                    self._place("drums", snare(self.sr), t, ramp * gain)
                    self.events.append({"t": round(t, 5), "kind": "snare"})
            if "hat" in layers:
                for step in range(spec.beats_per_bar * 2):
                    t = bar_time + step * self.beat / 2 + self._swing_offset(step)
                    accent = 0.75 if step % 2 else 0.42
                    self._place("drums", hat(self.sr), t, accent * gain)
                    self.events.append({"t": round(t, 5), "kind": "closed_hat"})
            if "openhat" in layers:
                for beat in range(spec.beats_per_bar):
                    t = bar_time + beat * self.beat + self.beat * 0.5
                    if beat % 2 == 1:
                        self._place("drums", hat(self.sr, open_hat=True), t, 0.5 * gain)
                        self.events.append({"t": round(t, 5), "kind": "open_hat"})
            if "ride" in layers:
                for beat in range(spec.beats_per_bar):
                    t = bar_time + beat * self.beat
                    self._place("drums", ride(self.sr), t, 0.4 * gain)
                    self.events.append({"t": round(t, 5), "kind": "ride"})

            # ---- bass ----------------------------------------------------
            if "bass" in layers:
                bass_midi = chord[0] - 12
                for step in range(spec.beats_per_bar * 2):
                    # Off-beat 8ths: the tech-house bass placement.
                    if step % 2 == 0:
                        continue
                    t = bar_time + step * self.beat / 2
                    n_samples = int(self.beat * 0.42 * self.sr)
                    freq = midi_to_hz(bass_midi)
                    tone = saw(freq, n_samples, self.sr, voices=2, detune_cents=8)
                    tone += sine(freq, n_samples, self.sr) * 0.6
                    env = adsr(n_samples, self.sr, 0.004, 0.06, 0.55, 0.05)
                    cutoff = 180 + 900 * env
                    self._place("bass", onepole_lp(tone * env, self.sr, cutoff) * 0.55, t, gain)

            # ---- chord stab ---------------------------------------------
            if "stab" in layers:
                for step in (2, 6):  # the "and" of 2 and the "and" of 4
                    t = bar_time + step * self.beat / 2
                    n_samples = int(self.beat * 0.5 * self.sr)
                    mix = np.zeros(n_samples, dtype=np.float32)
                    for note in chord[:3]:
                        mix += saw(midi_to_hz(note + 12), n_samples, self.sr,
                                   voices=3, detune_cents=14) * 0.33
                    env = adsr(n_samples, self.sr, 0.003, 0.09, 0.25, 0.12)
                    self._place("chords", onepole_lp(mix * env, self.sr, 3200) * 0.45, t, gain)

            # ---- arp ------------------------------------------------------
            if "arp" in layers:
                arp_notes = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[1] + 24]
                for step in range(spec.beats_per_bar * 4):
                    t = bar_time + step * self.beat / 4
                    note = arp_notes[step % len(arp_notes)]
                    n_samples = int(self.beat * 0.22 * self.sr)
                    tone = square(midi_to_hz(note), n_samples, self.sr)
                    env = adsr(n_samples, self.sr, 0.002, 0.04, 0.2, 0.04)
                    self._place("lead", onepole_lp(tone * env, self.sr, 5000) * 0.3, t, gain)

            # ---- pad ------------------------------------------------------
            if "pad" in layers:
                n_samples = int(self.bar * self.sr)
                mix = np.zeros(n_samples, dtype=np.float32)
                for note in chord:
                    mix += saw(midi_to_hz(note), n_samples, self.sr,
                               voices=5, detune_cents=22) * 0.25
                env = adsr(n_samples, self.sr, 0.35, 0.4, 0.75, 0.5)
                self._place("pad", onepole_lp(mix * env, self.sr, 2400) * 0.30, bar_time, gain)

    def _apply_sweep(self, section: SectionSpec, bar_offset: int) -> None:
        if section.sweep is None:
            return
        start = int(bar_offset * self.bar * self.sr)
        end = min(self.n, int((bar_offset + section.bars) * self.bar * self.sr))
        if end <= start:
            return
        cutoff = np.linspace(section.sweep[0], section.sweep[1], end - start)
        for bus in ("chords", "lead", "pad"):
            self.buses[bus][start:end] = onepole_lp(
                self.buses[bus][start:end], self.sr, cutoff
            )

    def _sidechain(self) -> np.ndarray:
        """Kick-triggered ducking envelope applied to the tonal buses."""
        env = np.ones(self.n, dtype=np.float32)
        shape_n = int(self.beat * 0.85 * self.sr)
        # Fast duck to 0.25, exponential recovery — a classic pumping curve.
        shape = 0.25 + 0.75 * (1.0 - np.exp(-np.linspace(0, 4.2, shape_n)))
        for event in self.events:
            if event["kind"] != "kick":
                continue
            start = int(event["t"] * self.sr)
            end = min(self.n, start + shape_n)
            if start >= self.n:
                continue
            env[start:end] = np.minimum(env[start:end], shape[: end - start])
        return env

    def render(self) -> tuple[np.ndarray, dict[str, np.ndarray], dict]:
        bar_offset = 0
        for section in self.spec.sections:
            self._render_section(section, bar_offset)
            self._apply_sweep(section, bar_offset)
            bar_offset += section.bars

        duck = self._sidechain()
        for bus in ("bass", "chords", "pad", "lead"):
            self.buses[bus] *= duck

        mix = sum(self.buses.values())

        # Master chain: gentle high-pass, bus glue, soft clip, then trim.
        mix = onepole_hp(mix, self.sr, 28.0)
        mix = np.tanh(mix * 1.15) * 0.92

        # Stereo: mid/side widening that keeps the low end mono.
        low = onepole_lp(mix, self.sr, 140.0)
        high = mix - low
        delay = int(0.008 * self.sr)
        side = np.zeros_like(high)
        side[delay:] = high[:-delay] * 0.35
        left = low + high + side
        right = low + high - side
        stereo = np.stack([left, right]).astype(np.float32)
        peak = float(np.max(np.abs(stereo)))
        if peak > 0:
            stereo *= 0.89 / peak

        truth = self._ground_truth()
        return stereo, self.buses, truth

    def _ground_truth(self) -> dict:
        spec = self.spec
        sections = []
        bar = 0
        for section in spec.sections:
            sections.append({
                "label": section.label,
                "start_bar": bar + 1,
                "bars": section.bars,
                "start_time": round(bar * self.bar, 4),
                "end_time": round((bar + section.bars) * self.bar, 4),
                "layers": list(section.layers),
            })
            bar += section.bars
        return {
            "name": spec.name,
            "bpm": spec.bpm,
            "key": f"{spec.key_root} {spec.key_mode}",
            "key_root_pc": PITCH_CLASSES.index(_ALIASES.get(spec.key_root, spec.key_root)),
            "key_mode": spec.key_mode,
            "time_signature": f"{spec.beats_per_bar}/4",
            "swing": spec.swing,
            "total_bars": self.total_bars,
            "duration": round(self.total_bars * self.bar, 4),
            "bar_seconds": round(self.bar, 6),
            "beat_seconds": round(self.beat, 6),
            "progression_semitones": list(spec.progression),
            "chord_qualities": list(spec.chord_quality),
            "sections": sections,
            "drum_events": len(self.events),
            "downbeat_times": [round(i * self.bar, 5) for i in range(self.total_bars)],
            "beat_times": [
                round(i * self.beat, 5)
                for i in range(self.total_bars * spec.beats_per_bar)
            ],
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_wav(path: Path, data: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import soundfile as sf

        sf.write(str(path), data.T if data.ndim == 2 else data, sr, subtype="PCM_24")
        return
    except Exception:
        pass
    import wave

    arr = data.T if data.ndim == 2 else data[:, None]
    ints = np.clip(arr * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(arr.shape[1])
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(ints.tobytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--preset", default="techhouse", choices=sorted(PRESETS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--bpm", type=float, default=None)
    parser.add_argument("--key", default=None, help='e.g. "Am", "F#m", "C"')
    parser.add_argument("--stems", action="store_true", help="also write the ground-truth stems")
    parser.add_argument("--list-presets", action="store_true")
    args = parser.parse_args(argv)

    if args.list_presets:
        for name, spec in PRESETS.items():
            print(f"{name:<12} {spec.bpm:>5.0f} BPM  {spec.key_root} {spec.key_mode}  {spec.name}")
        return 0

    spec = PRESETS[args.preset]
    if args.bpm:
        spec.bpm = args.bpm
    if args.key:
        raw = args.key.strip()
        mode = "minor" if raw.endswith("m") else "major"
        root = raw[:-1] if raw.endswith("m") else raw
        spec.key_root, spec.key_mode = root, mode

    out_dir = Path(__file__).parent / "generated"
    out = args.out or out_dir / f"retrack_demo_{args.preset}.wav"

    print(f"Rendering '{spec.name}' — {spec.bpm} BPM, {spec.key_root} {spec.key_mode} ...")
    renderer = Renderer(spec)
    mix, buses, truth = renderer.render()

    _write_wav(out, mix, SR)
    truth_path = out.with_suffix(".truth.json")
    truth_path.write_text(json.dumps(truth, indent=2), encoding="utf-8")

    print(f"  audio        {out}  ({truth['duration']:.1f} s, {truth['total_bars']} bars)")
    print(f"  ground truth {truth_path}")

    if args.stems:
        stem_dir = out.parent / f"{out.stem}_stems"
        for name, data in buses.items():
            if np.max(np.abs(data)) < 1e-6:
                continue
            stem_path = stem_dir / f"{name}.wav"
            _write_wav(stem_path, data / max(np.max(np.abs(data)), 1e-9) * 0.85, SR)
            print(f"  stem         {stem_path}")

    print("\nNow try:")
    print(f'  retrack analyze "{out}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
