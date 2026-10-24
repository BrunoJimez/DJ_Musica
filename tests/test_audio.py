"""Audio I/O, DSP and loudness metering."""

from __future__ import annotations

import numpy as np
import pytest

from retrack.audio import dsp
from retrack.audio.io import AudioBuffer, audio_fingerprint_key, load_audio, save_audio
from retrack.audio.loudness import measure_loudness, true_peak


class TestBuffer:
    def test_mono_is_still_two_dimensional(self):
        buffer = AudioBuffer(np.zeros(1000, dtype=np.float32), 44100)
        assert buffer.samples.ndim == 2
        assert buffer.channels == 1
        assert buffer.frames == 1000

    def test_transposed_input_is_corrected(self):
        # (frames, channels) is the classic mix-up; the buffer must fix it.
        buffer = AudioBuffer(np.zeros((5000, 2), dtype=np.float32), 44100)
        assert buffer.channels == 2
        assert buffer.frames == 5000

    def test_mid_side_roundtrip(self):
        left = np.random.default_rng(0).standard_normal(2000).astype(np.float32)
        right = np.random.default_rng(1).standard_normal(2000).astype(np.float32)
        buffer = AudioBuffer(np.stack([left, right]), 44100)
        mid, side = buffer.mid_side()
        np.testing.assert_allclose(mid + side, left, atol=1e-6)
        np.testing.assert_allclose(mid - side, right, atol=1e-6)

    def test_roundtrip_through_disk(self, tmp_path):
        data = (np.random.default_rng(2).standard_normal((2, 8000)) * 0.3).astype(np.float32)
        path = tmp_path / "t.wav"
        save_audio(AudioBuffer(data, 44100), path)
        loaded = load_audio(path)
        assert loaded.channels == 2
        assert abs(loaded.frames - 8000) <= 1
        assert loaded.sr == 44100

    def test_fingerprint_key_is_content_based(self, tmp_path):
        data = (np.random.default_rng(3).standard_normal((2, 40000)) * 0.3).astype(np.float32)
        a, b = tmp_path / "a.wav", tmp_path / "b.wav"
        save_audio(AudioBuffer(data, 44100), a)
        save_audio(AudioBuffer(data, 44100), b)
        assert audio_fingerprint_key(a) == audio_fingerprint_key(b)

        save_audio(AudioBuffer(data * 0.5, 44100), b)
        assert audio_fingerprint_key(a) != audio_fingerprint_key(b)


class TestDSP:
    def test_stft_istft_reconstructs(self):
        sr = 44100
        x = (0.5 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr)).astype(np.float32)
        spectrum = dsp.stft(x, 2048, 512)
        y = dsp.istft(spectrum, 512, length=x.size)
        assert y.size == x.size
        # Reconstruction must hold to float32 precision across the whole
        # signal, including the tail — the tail is where a naive centre-trim
        # silently drops up to a hop of real audio.
        assert np.max(np.abs(y - x)) < 1e-5

    def test_stft_matches_librosa(self):
        librosa = pytest.importorskip("librosa")
        sr = 22050
        x = np.random.default_rng(4).standard_normal(sr).astype(np.float32) * 0.2
        ours = np.abs(dsp.stft(x, 2048, 512))
        theirs = np.abs(librosa.stft(x, n_fft=2048, hop_length=512))
        assert ours.shape == theirs.shape
        assert np.max(np.abs(ours - theirs)) < 1e-3

    def test_pitch_conversions(self):
        assert dsp.hz_to_midi(440.0) == pytest.approx(69.0)
        assert dsp.midi_to_hz(69) == pytest.approx(440.0)
        assert dsp.midi_to_name(69) == "A4"
        assert dsp.midi_to_name(60) == "C4"

    def test_beat_conversions(self):
        assert dsp.beats_to_seconds(4, 120) == pytest.approx(2.0)
        assert dsp.seconds_to_beats(2.0, 120) == pytest.approx(4.0)

    @pytest.mark.parametrize("kind", ["lowpass", "highpass", "peaking", "lowshelf", "highshelf"])
    def test_biquads_are_stable(self, kind):
        b, a = dsp.biquad_coeffs(kind, 44100, 1000.0, 0.707, 6.0)
        # All poles inside the unit circle.
        assert np.all(np.abs(np.roots(a)) < 1.0)

    def test_crest_factor_of_sine(self):
        x = np.sin(2 * np.pi * np.arange(44100) / 100)
        # A sine's peak-to-RMS ratio is sqrt(2), i.e. 3.01 dB.
        assert dsp.crest_factor(x) == pytest.approx(3.01, abs=0.05)

    def test_peak_pick_finds_impulses(self):
        x = np.zeros(1000, dtype=np.float32)
        x[[100, 300, 700]] = 1.0
        peaks = dsp.peak_pick(x, delta=0.1)
        assert set(peaks.tolist()) == {100, 300, 700}


class TestLoudness:
    def test_bs1770_conformance_stereo(self, sine_stereo):
        """ITU-R BS.2217 case: -23 dBFS 1 kHz on both channels reads -23 LUFS."""
        samples, sr = sine_stereo
        report = measure_loudness(samples, sr)
        assert report.integrated_lufs == pytest.approx(-23.0, abs=0.1)

    def test_bs1770_conformance_mono_channel(self, sine_stereo):
        """The same tone on one channel of two reads 3 dB lower."""
        samples, sr = sine_stereo
        mono = samples[:1]
        report = measure_loudness(mono, sr)
        assert report.integrated_lufs == pytest.approx(-26.0, abs=0.1)

    def test_true_peak_detects_intersample(self):
        sr = 44100
        # A tone just off Nyquist/4 produces inter-sample peaks above the
        # sample peak — the whole reason true-peak metering exists.
        x = 0.99 * np.sin(2 * np.pi * 11025.7 * np.arange(sr) / sr)
        sample_peak = 20 * np.log10(np.max(np.abs(x)))
        assert true_peak(x[np.newaxis, :], sr) > sample_peak

    def test_silence_does_not_crash(self):
        report = measure_loudness(np.zeros((2, 44100), dtype=np.float32), 44100)
        assert not np.isfinite(report.integrated_lufs)

    def test_verdict_is_reported(self, demo_mono):
        samples, sr, _truth = demo_mono
        report = measure_loudness(samples[np.newaxis, :], sr)
        label, why = report.mastering_verdict()
        assert label
        assert len(why) > 20
