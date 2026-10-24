"""Analysis accuracy, asserted against synthetic ground truth."""

from __future__ import annotations

import numpy as np
import pytest

from retrack.analysis.features import PITCH_CLASSES


class TestRhythm:
    def test_bpm_is_essentially_exact(self, demo_mono, demo_track):
        """A grid-quantised track should be recovered to well under 0.1 BPM.

        This is the regression test for the median-of-intervals period
        estimate, which was wrong by 1.2 BPM at 128.
        """
        from retrack.analysis.rhythm import analyze_rhythm

        samples, sr, truth = demo_mono
        rhythm = analyze_rhythm(samples, sr, source_path=str(demo_track[0]))
        assert rhythm.bpm.value == pytest.approx(truth["bpm"], abs=0.05)

    def test_beats_land_on_the_beats(self, demo_mono, demo_track):
        from retrack.analysis.rhythm import analyze_rhythm

        samples, sr, truth = demo_mono
        rhythm = analyze_rhythm(samples, sr, source_path=str(demo_track[0]))

        true_beats = np.asarray(truth["beat_times"])
        errors = np.array([np.min(np.abs(rhythm.beats - t)) for t in true_beats])
        assert np.median(errors) < 0.020
        # The MIREX convention is a 70 ms tolerance window.
        assert (errors < 0.070).mean() > 0.98

    def test_downbeats_and_first_bar(self, demo_mono, demo_track):
        from retrack.analysis.rhythm import analyze_rhythm

        samples, sr, truth = demo_mono
        rhythm = analyze_rhythm(samples, sr, source_path=str(demo_track[0]))

        assert rhythm.downbeats.size >= 60
        # Bar 1 must exist: every bar number in the project is counted from it.
        assert rhythm.downbeats[0] < 0.05

        true_downbeats = np.asarray(truth["downbeat_times"])
        errors = np.array([np.min(np.abs(rhythm.downbeats - t)) for t in true_downbeats])
        assert (errors < 0.070).mean() > 0.95

    def test_time_signature(self, demo_mono, demo_track):
        from retrack.analysis.rhythm import analyze_rhythm

        samples, sr, _truth = demo_mono
        rhythm = analyze_rhythm(samples, sr, source_path=str(demo_track[0]))
        assert rhythm.time_signature.numerator == 4

    def test_constant_tempo_is_recognised(self, demo_mono, demo_track):
        from retrack.analysis.rhythm import analyze_rhythm

        samples, sr, _truth = demo_mono
        rhythm = analyze_rhythm(samples, sr, source_path=str(demo_track[0]))
        assert rhythm.is_constant_tempo

    @pytest.mark.slow
    def test_no_tempo_octave_error_on_dnb(self, demo_dnb):
        """174 BPM must not be reported as 87 — the classic halving failure."""
        from retrack.analysis.rhythm import analyze_rhythm
        from retrack.audio.io import load_audio

        path, truth = demo_dnb
        buffer = load_audio(path, sr=44100, mono=True)
        rhythm = analyze_rhythm(buffer.mono(), buffer.sr, source_path=str(path))
        assert rhythm.bpm.value == pytest.approx(truth["bpm"], abs=0.5)

    @pytest.mark.slow
    def test_swing_is_detected_and_not_invented(self, demo_swing, demo_mono):
        """A swung track reads swung; a straight one reads straight."""
        from retrack.analysis.rhythm import analyze_rhythm
        from retrack.audio.io import load_audio

        path, truth = demo_swing
        buffer = load_audio(path, sr=44100, mono=True)
        swung = analyze_rhythm(buffer.mono(), buffer.sr, source_path=str(path))
        assert swung.swing_ratio == pytest.approx(truth["swing"], abs=0.05)

        samples, sr, straight_truth = demo_mono
        straight = analyze_rhythm(samples, sr)
        assert straight_truth["swing"] == 0.5
        assert straight.swing_ratio == pytest.approx(0.5, abs=0.02)


class TestTonal:
    @pytest.mark.slow
    def test_key_is_correct(self, demo_mono):
        """Regression test for the relative-major confusion.

        Before the chroma high-pass and the chord-function re-ranking, this
        reported C major for an A minor track.
        """
        from retrack.analysis.rhythm import analyze_rhythm
        from retrack.analysis.tonal import analyze_tonal

        samples, sr, truth = demo_mono
        rhythm = analyze_rhythm(samples, sr)
        tonal = analyze_tonal(
            samples, sr, beats=rhythm.beats, downbeats=rhythm.downbeats
        )
        assert tonal.key_root == truth["key_root_pc"]
        assert tonal.key_mode == truth["key_mode"]

    @pytest.mark.slow
    def test_chord_progression(self, demo_mono):
        from retrack.analysis.rhythm import analyze_rhythm
        from retrack.analysis.tonal import analyze_tonal

        samples, sr, truth = demo_mono
        rhythm = analyze_rhythm(samples, sr)
        tonal = analyze_tonal(
            samples, sr, beats=rhythm.beats, downbeats=rhythm.downbeats
        )

        expected = []
        for semitone, quality in zip(
            truth["progression_semitones"], truth["chord_qualities"], strict=False
        ):
            pitch_class = (truth["key_root_pc"] + semitone) % 12
            expected.append(PITCH_CLASSES[pitch_class] + ("m" if quality == "min" else ""))

        detected = [c.label.split("/")[0] for c in tonal.chords[:4]]
        # Allow extensions (Cadd9 for C) but the root and quality must match.
        for got, want in zip(detected, expected, strict=False):
            assert got.startswith(want), f"{got!r} does not match {want!r}"

    def test_camelot_mapping(self):
        from retrack.analysis.features import CAMELOT

        assert CAMELOT[(9, "minor")] == "8A"  # A minor
        assert CAMELOT[(0, "major")] == "8B"  # C major — its relative
        assert CAMELOT[(5, "minor")] == "4A"  # F minor

    def test_viterbi_can_change_chords(self):
        """Guards the change-cost formulation.

        Expressed as a self-transition probability, the decoder collapsed every
        chord in a track into one.
        """
        import numpy as np

        from retrack.analysis.tonal import _viterbi_smooth

        scores = np.full((24, 40), -0.5)
        scores[3, :20] = 0.9
        scores[7, 20:] = 0.9
        path = _viterbi_smooth(scores)
        assert path[0] == 3
        assert path[-1] == 7
        assert len(set(path.tolist())) == 2


class TestStructure:
    @pytest.mark.slow
    def test_section_boundaries(self, analysis, demo_track):
        _path, truth = demo_track
        assert analysis.structure is not None

        detected = {s.start_bar for s in analysis.structure.segments}
        expected = {s["start_bar"] for s in truth["sections"]}
        # Every true boundary must be found (extra subdivisions are acceptable).
        missing = expected - detected
        assert not missing, f"missed section boundaries at bars {sorted(missing)}"

    @pytest.mark.slow
    def test_repeated_sections_share_a_cluster(self, analysis):
        segments = analysis.structure.segments
        drops = [s for s in segments if s.label == "drop" and s.bar_length >= 16]
        assert len(drops) >= 2
        assert drops[0].cluster == drops[1].cluster

    @pytest.mark.slow
    def test_mix_points_exist(self, analysis):
        assert analysis.structure.mix_in_points
        assert analysis.structure.mix_out_points


class TestDrums:
    @pytest.mark.slow
    def test_kick_is_found_on_the_beat(self, analysis):
        assert analysis.drums is not None
        pattern = analysis.drums.patterns.get("kick")
        assert pattern, "no kick pattern detected"
        quarter = analysis.drums.steps_per_bar // 4
        on_beats = [pattern[i * quarter] > 0.05 for i in range(4)]
        assert sum(on_beats) >= 3, "four-on-the-floor kick not recovered"

    @pytest.mark.slow
    def test_groove_is_named(self, analysis):
        assert "four-on-the-floor" in analysis.drums.groove_name

    def test_prototypes_classify_their_own_reference_sounds(self):
        """Each measured prototype must classify back to itself.

        This is the regression test for hand-written prototype values: the
        kick's spectral centroid was written as 0.13 when the measured value
        is 0.69, and every four-on-the-floor kick came out as a tom.
        """
        import numpy as np

        from retrack.analysis.drums import _PROTOTYPES, classify_hits

        names = list(_PROTOTYPES)
        features = np.array([_PROTOTYPES[n] for n in names], dtype=np.float32)
        labels, _confidence = classify_hits(features, adapt=False)
        assert labels == names

    def test_perc_is_a_threshold_not_a_competitor(self):
        """`perc` must never appear in the prototype table.

        As a catch-all prototype with low weights it had a small weighted
        distance to everything and swallowed the entire kit — the classifier
        reported one class for the whole track.
        """
        from retrack.analysis.drums import _PROTOTYPES

        assert "perc" not in _PROTOTYPES


class TestPipeline:
    @pytest.mark.slow
    def test_full_analysis_populates_everything(self, analysis):
        assert analysis.rhythm is not None
        assert analysis.tonal is not None
        assert analysis.structure is not None
        assert analysis.drums is not None
        assert analysis.timbre is not None
        assert analysis.mix is not None
        assert analysis.stems
        assert analysis.genre

    @pytest.mark.slow
    def test_serialises_and_restores(self, analysis):
        import json

        from retrack.analysis.pipeline import _from_dict

        payload = json.dumps(analysis.to_dict())
        restored = _from_dict(json.loads(payload))
        assert restored.bpm == pytest.approx(analysis.bpm, abs=0.01)
        assert restored.key_name == analysis.key_name
        assert len(restored.structure.segments) == len(analysis.structure.segments)

    @pytest.mark.slow
    def test_genre_guess_is_plausible(self, analysis):
        names = [name for name, _p in analysis.genre[:3]]
        assert any(g in names for g in ("house", "tech house", "techno"))

    @pytest.mark.slow
    def test_stem_shares_sum_to_one(self, analysis):
        total = sum(s.energy_share for s in analysis.stems.values())
        assert total == pytest.approx(1.0, abs=0.02)
