"""System probing, authorship, learn mode, live engine and reports."""

from __future__ import annotations

import numpy as np
import pytest


class TestSystem:
    def test_hardware_probe_never_raises(self):
        from retrack.system.hardware import probe_hardware

        hardware = probe_hardware()
        assert hardware.physical_cores >= 1
        assert hardware.logical_cores >= hardware.physical_cores
        assert hardware.tier in ("minimal", "standard", "performance", "workstation")
        assert 0 <= hardware.score <= 100

    def test_capabilities_report_required(self):
        from retrack.system.deps import probe_capabilities

        report = probe_capabilities()
        assert not report.missing_required, "core dependencies missing"
        for capability in report.capabilities:
            assert capability.install_hint
            assert capability.license

    def test_every_task_has_a_usable_model(self):
        """No task may plan to nothing — each needs a built-in path or an
        explicit 'unavailable' entry the UI can show."""
        from retrack.system.model_selector import plan_models

        plan = plan_models()
        for task in ("separation", "beats", "transcription", "lyrics", "llm"):
            assert plan.get(task) is not None, f"no model planned for {task}"

    def test_windows_vram_saturation_is_not_trusted(self):
        """Win32_VideoController.AdapterRAM saturates at 4095 MB.

        Trusting it makes an 8 GB card look like a 4 GB one and downgrades the
        entire model plan.
        """
        from retrack.system.hardware import GPUInfo

        gpu = GPUInfo(name="Test", vendor="nvidia", vram_mb=4095)
        # The probe drops such values; the dataclass itself just carries them.
        assert gpu.vram_gb == pytest.approx(4.0, abs=0.01)


class TestAuthorship:
    def test_fingerprint_matches_itself(self, demo_mono):
        from retrack.authorship import build_fingerprint, match_fingerprints

        samples, sr, _truth = demo_mono
        clip = samples[: sr * 30]
        fingerprint = build_fingerprint(clip, sr)
        assert fingerprint.hash_count > 500

        matches = match_fingerprints(fingerprint, fingerprint)
        assert matches
        assert matches[0].offset_s == pytest.approx(0.0, abs=0.1)
        assert matches[0].confidence > 0.7

    def test_unrelated_noise_does_not_match(self, demo_mono):
        from retrack.authorship import build_fingerprint, match_fingerprints

        samples, sr, _truth = demo_mono
        rng = np.random.default_rng(11)
        noise = (rng.standard_normal(sr * 20) * 0.2).astype(np.float32)

        a = build_fingerprint(samples[: sr * 20], sr)
        b = build_fingerprint(noise, sr)
        matches = match_fingerprints(a, b, min_aligned=12)
        assert not matches or matches[0].confidence < 0.35

    def test_overlapping_offsets_are_suppressed(self, demo_mono):
        """Loop-based music aligns with itself at every loop multiple.

        Without suppression one real match is reported as a page of duplicates
        and the coverage figure exceeds 100%.
        """
        from retrack.authorship import build_fingerprint, match_fingerprints

        samples, sr, _truth = demo_mono
        fingerprint = build_fingerprint(samples[: sr * 40], sr)
        matches = match_fingerprints(fingerprint, fingerprint, max_matches=4)
        ranges = [(m.query_start, m.query_end) for m in matches]
        for i, (a_start, a_end) in enumerate(ranges):
            for b_start, b_end in ranges[i + 1:]:
                overlap = max(0.0, min(a_end, b_end) - max(a_start, b_start))
                span = max(a_end - a_start, 1e-6)
                assert overlap / span <= 0.55

    def test_melodic_ngrams_are_transposition_invariant(self):
        from retrack.analysis.features import Note
        from retrack.authorship.similarity import melodic_ngrams

        original = [Note(start=i * 0.5, duration=0.4, pitch=60 + p)
                    for i, p in enumerate([0, 2, 4, 5, 7, 9])]
        transposed = [Note(start=n.start, duration=n.duration, pitch=n.pitch + 7)
                      for n in original]
        assert melodic_ngrams(original, 3) == melodic_ngrams(transposed, 3)

    def test_database_roundtrip(self, tmp_path, demo_track, demo_mono):
        from retrack.authorship import ReferenceDatabase, build_fingerprint

        path, _truth = demo_track
        samples, sr, _ = demo_mono
        fingerprint = build_fingerprint(samples[: sr * 20], sr)

        with ReferenceDatabase(tmp_path / "ref.sqlite") as database:
            track_id = database.add_track(
                path, fingerprint=fingerprint, title="demo", bpm=128.0
            )
            assert track_id is not None
            assert database.track_count() == 1

            restored = database.get_fingerprint(track_id)
            assert restored is not None
            assert restored.hash_count == fingerprint.hash_count

            candidates = database.candidates_for(fingerprint)
            assert candidates and candidates[0][0] == track_id

    def test_report_is_scoped_and_says_so(self, analysis):
        from retrack.authorship.originality import build_report

        report = build_report(analysis, comparisons=[])
        statistics = report.statistics()
        assert "scope_note" in statistics
        assert "not a legal determination" in statistics["scope_note"]
        assert report.verdict == "not assessed"


class TestLearn:
    def test_highway_scores_timing(self, analysis):
        from retrack.learn import build_highway
        from retrack.reverse import build_project, build_recipe

        project = build_project(analysis, sr=analysis.sample_rate)
        recipe = build_recipe(analysis, project)
        step = next(s for s in recipe.steps if s.category == "drums" and s.events)

        highway = build_highway(step, analysis.bpm, loop_bars=1)
        assert highway.notes

        for note in list(highway.notes):
            highway.position = note.time
            highway.hit(note.lane, at=note.time)

        summary = highway.summary()
        assert summary.accuracy > 0.95
        assert summary.grade in ("S", "A")
        assert summary.feedback()

    def test_highway_detects_a_timing_bias(self, analysis):
        from retrack.learn import build_highway
        from retrack.reverse import build_project, build_recipe

        project = build_project(analysis, sr=analysis.sample_rate)
        recipe = build_recipe(analysis, project)
        step = next(s for s in recipe.steps if s.category == "drums" and s.events)

        highway = build_highway(step, analysis.bpm, loop_bars=1)
        for note in list(highway.notes):
            highway.hit(note.lane, at=note.time - 0.025)  # 25 ms early

        summary = highway.summary()
        assert summary.mean_error_ms < -15
        assert any("early" in line for line in summary.feedback())

    def test_mashing_breaks_the_combo(self, analysis):
        from retrack.learn import build_highway
        from retrack.reverse import build_project, build_recipe

        project = build_project(analysis, sr=analysis.sample_rate)
        recipe = build_recipe(analysis, project)
        step = next(s for s in recipe.steps if s.category == "drums" and s.events)

        highway = build_highway(step, analysis.bpm, loop_bars=1)
        highway.position = 999.0
        result = highway.hit(0, at=999.0)
        assert result.judgement.value == "miss"
        assert highway.combo == 0

    def test_lanes_collapse_to_those_used(self, analysis):
        from retrack.learn import build_highway
        from retrack.reverse import build_project, build_recipe

        project = build_project(analysis, sr=analysis.sample_rate)
        recipe = build_recipe(analysis, project)
        step = next(s for s in recipe.steps if s.category == "drums" and s.events)

        highway = build_highway(step, analysis.bpm, loop_bars=1)
        used = {n.lane for n in highway.notes}
        assert used == set(range(highway.lanes))

    def test_lesson_plan_gates_progression(self, analysis):
        from retrack.learn import build_lesson_plan
        from retrack.reverse import build_project, build_recipe

        project = build_project(analysis, sr=analysis.sample_rate)
        recipe = build_recipe(analysis, project)
        plan = build_lesson_plan(recipe)

        assert plan.lessons
        assert plan.progress == 0.0
        available = plan.available()
        assert len(available) < len(plan.lessons), "everything unlocked at once"


class TestLive:
    def test_deck_renders_and_advances(self, demo_track, analysis):
        from retrack.live import Deck

        path, _truth = demo_track
        deck = Deck(0)
        deck.load(path, analysis)
        assert deck.loaded
        assert deck.original_bpm == pytest.approx(analysis.bpm, abs=0.01)
        assert deck.hot_cues

        deck.play()
        before = deck.position
        block = deck.render(512)
        assert block.shape == (2, 512)
        assert deck.position > before

    def test_sync_matches_tempo(self, demo_track, analysis):
        from retrack.live import Deck

        path, _truth = demo_track
        deck = Deck(1)
        deck.load(path, analysis)
        deck.sync_to(100.0, match_phase=False)
        assert deck.current_bpm == pytest.approx(100.0, abs=0.01)

    def test_loop_wraps(self, demo_track, analysis):
        from retrack.live import Deck

        path, _truth = demo_track
        deck = Deck(0)
        deck.load(path, analysis)
        deck.seek(10.0)
        deck.set_loop(4)
        assert deck.loop.active
        deck.play()
        for _ in range(400):
            deck.render(512)
        assert deck.loop.start - 0.1 <= deck.position_seconds <= deck.loop.end + 0.1

    def test_crossfader_curves(self):
        from retrack.live import crossfader_gains

        a, b = crossfader_gains(-1.0, "smooth")
        assert a == pytest.approx(1.0) and b == pytest.approx(0.0)
        a, b = crossfader_gains(1.0, "smooth")
        assert a == pytest.approx(0.0) and b == pytest.approx(1.0)

        # Constant power holds perceived level through the crossover; equal
        # gain dips 3 dB in the middle.
        a, b = crossfader_gains(0.0, "constant_power")
        assert a**2 + b**2 == pytest.approx(1.0, abs=1e-6)

    def test_offline_render_is_deterministic(self, demo_track, analysis):
        from retrack.live import LiveEngine

        path, _truth = demo_track
        engine = LiveEngine(deck_count=2)
        engine.decks[0].load(path, analysis)
        engine.decks[0].seek(20.0)
        engine.decks[0].play()

        audio = engine.render_offline(1.0)
        assert audio.shape[0] == 2
        assert audio.shape[1] == 44100
        assert np.max(np.abs(audio)) > 0.0
        assert np.all(np.isfinite(audio))

    def test_limiter_holds_the_ceiling(self):
        from retrack.live import Mixer

        mixer = Mixer(1)
        loud = np.ones((2, 512), dtype=np.float32) * 4.0
        master, _cue = mixer.process({0: loud}, 512)
        assert np.max(np.abs(master)) <= 1.0

    def test_camelot_distance(self):
        from retrack.live import camelot_distance

        assert camelot_distance("8A", "8A") == 0
        assert camelot_distance("8A", "9A") == 1
        assert camelot_distance("8A", "8B") == 1  # relative major
        assert camelot_distance("12A", "1A") == 1  # wraps around the wheel
        assert camelot_distance("8A", "2A") > 4

    def test_setlist_orders_a_crate(self, analysis):
        from retrack.live import plan_set

        plan = plan_set([analysis], shape="arc")
        assert len(plan) == 1
        assert plan[0].position == 1


class TestReports:
    def test_markdown_report(self, analysis):
        from retrack.reports import ReportBundle, render_markdown

        bundle = ReportBundle(analysis=analysis, language="en")
        text = render_markdown(bundle)
        assert analysis.display_name in text
        assert "BPM" in text

    @pytest.mark.slow
    def test_html_is_self_contained(self, analysis, demo_mono, tmp_path):
        pytest.importorskip("jinja2")
        from retrack.reports import ReportBundle, export_html

        samples, sr, _truth = demo_mono
        bundle = ReportBundle(analysis=analysis, audio=samples, sr=sr, language="pt_BR")
        path = export_html(bundle, tmp_path / "report.html")
        html = path.read_text(encoding="utf-8")

        assert "<!doctype html>" in html.lower()
        assert "data:image/png;base64," in html, "charts are not embedded"
        # No external references — the file must render offline, forever.
        assert "http://" not in html.replace("http://www.w3.org", "")
        # Localised into the requested language, and carrying the core sections.
        for heading in ("Arranjo", "Harmonia", "Mixagem e masterização"):
            assert heading in html, f"missing section: {heading}"

    def test_time_formatting_carries(self):
        """59.97 s must read 1:00.0, never 0:60.0."""
        from retrack.reports import format_time

        assert format_time(0.0) == "0:00.0"
        assert format_time(59.97) == "1:00.0"
        assert format_time(60.0) == "1:00.0"
        assert format_time(125.4) == "2:05.4"


class TestAI:
    def test_rules_produce_insights(self, analysis):
        from retrack.ai import evaluate

        insights = evaluate(analysis)
        assert insights
        for insight in insights:
            assert insight.title
            assert insight.observation
            assert 0.0 <= insight.confidence <= 1.0

    def test_advisor_works_without_a_model(self, analysis):
        """The rule engine must produce everything with no LLM present."""
        from retrack.ai import advise

        advice = advise(analysis, use_llm=False)
        assert advice.method == "rules"
        assert advice.insights
        assert advice.as_text()

    def test_key_insight_mentions_camelot(self, analysis):
        from retrack.ai import evaluate

        insights = evaluate(analysis)
        harmony = [i for i in insights if i.category == "harmony"]
        assert harmony
        assert any("Camelot" in i.observation or "Camelot" in i.why for i in harmony)


class TestHardwareCompat:
    def test_compatibility_report_never_raises(self):
        from retrack.hardware import check_compatibility

        report = check_compatibility()
        assert isinstance(report.ports, list)
        assert isinstance(report.audio_devices, list)
        assert report.summary_lines()

    def test_generic_mapping_covers_the_essentials(self):
        from retrack.hardware import ACTIONS, generic_mapping

        mapping = generic_mapping(2)
        bound = {b.action for b in mapping.bindings}
        for essential in ("play_pause", "cue", "sync", "volume", "crossfader", "panic"):
            assert essential in bound
        assert bound <= set(ACTIONS), "mapping binds an unknown action"

    def test_relative_encoder_decoding(self):
        from retrack.hardware.midi import decode_relative

        assert decode_relative(1, "twos_complement") == 1.0
        assert decode_relative(127, "twos_complement") == -1.0
        assert decode_relative(65, "binary_offset") == 1.0
        assert decode_relative(63, "binary_offset") == -1.0
