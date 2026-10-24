"""Project reconstruction, the build recipe, and every exporter."""

from __future__ import annotations

import gzip
import json
import zipfile
from xml.etree import ElementTree as ET

import pytest


@pytest.fixture(scope="module")
def project(analysis):
    from retrack.reverse import build_project

    return build_project(analysis, sr=analysis.sample_rate)


@pytest.fixture(scope="module")
def recipe(analysis, project):
    from retrack.reverse import build_recipe

    return build_recipe(analysis, project)


class TestProject:
    def test_basic_shape(self, project, analysis):
        assert project.bpm == pytest.approx(analysis.bpm, abs=0.01)
        assert project.tracks
        assert project.length_beats > 0
        assert 0.0 <= project.confidence <= 1.0

    def test_track_names_are_unique(self, project):
        """Three tracks all called 'Stab' is ambiguous in every export format."""
        names = [t.name for t in project.tracks]
        assert len(names) == len(set(names))

    def test_beat_second_conversions_are_inverse(self, project):
        for beat in (0.0, 16.0, 123.5):
            seconds = project.beats_to_seconds(beat)
            assert project.seconds_to_beats(seconds) == pytest.approx(beat, abs=1e-6)

    def test_markers_cover_the_sections(self, project, analysis):
        section_markers = project.markers_of("section")
        assert len(section_markers) >= len(analysis.structure.segments) - 1

    def test_caveats_are_present(self, project):
        """The reconstruction must state its own limits."""
        assert project.notes
        assert any("inferred" in n.lower() for n in project.notes)


class TestRecipe:
    def test_steps_are_ordered_and_numbered(self, recipe):
        assert recipe.steps
        assert [s.index for s in recipe.steps] == list(range(1, len(recipe.steps) + 1))

    def test_setup_comes_first(self, recipe):
        assert recipe.steps[0].category == "setup"

    def test_drum_steps_carry_playable_events(self, recipe):
        drum_steps = [s for s in recipe.steps if s.category == "drums" and s.events]
        assert drum_steps
        for step in drum_steps:
            assert all(e.beat >= 0 for e in step.events)
            assert step.lane_map

    def test_every_step_explains_itself(self, recipe):
        for step in recipe.steps:
            assert len(step.explanation) > 40, f"step {step.index} has no real explanation"

    def test_text_rendering(self, recipe):
        text = recipe.as_text()
        assert "HOW TO BUILD" in text
        assert str(recipe.steps[0].title) in text


class TestExporters:
    def test_midi(self, project, tmp_path):
        mido = pytest.importorskip("mido")
        from retrack.reverse.exporters import export_midi

        path = export_midi(project, tmp_path / "out.mid")
        assert path.exists()

        midi = mido.MidiFile(str(path))
        assert midi.type == 1
        assert len(midi.tracks) >= 2
        notes = sum(
            1 for track in midi.tracks for message in track if message.type == "note_on"
        )
        assert notes > 50

    def test_dawproject_is_valid_zip_and_xml(self, project, tmp_path):
        from retrack.reverse.exporters import export_dawproject

        path = export_dawproject(project, tmp_path / "out.dawproject")
        with zipfile.ZipFile(path) as archive:
            assert set(archive.namelist()) >= {"project.xml", "metadata.xml"}
            root = ET.fromstring(archive.read("project.xml"))
            assert root.tag == "Project"
            assert root.findall(".//Track")
            assert root.findall(".//Note")
            ET.fromstring(archive.read("metadata.xml"))

    def test_reaper_blocks_balance(self, project, tmp_path):
        from retrack.reverse.exporters import export_reaper

        path = export_reaper(project, tmp_path / "out.rpp")
        text = path.read_text(encoding="utf-8")
        opens = sum(
            text.count(tag)
            for tag in ("<REAPER_PROJECT", "<NOTES", "<TRACK", "<ITEM", "<SOURCE")
        )
        closes = sum(1 for line in text.splitlines() if line.strip() == ">")
        assert opens == closes, "unbalanced RPP blocks"
        assert "TEMPO" in text

    def test_ableton_is_gzipped_xml(self, project, tmp_path):
        from retrack.reverse.exporters import export_ableton

        path = export_ableton(project, tmp_path / "out.als")
        root = ET.fromstring(gzip.open(path).read())
        assert root.tag == "Ableton"
        assert root.findall(".//MidiTrack")

    def test_json_roundtrip(self, project, tmp_path):
        from retrack.reverse.exporters import export_json

        path = export_json(project, tmp_path / "out.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["project"]["bpm"] == pytest.approx(project.bpm, abs=0.01)
        assert payload["project"]["statistics"]["tracks"] == len(project.tracks)

    def test_rekordbox_xml(self, project, analysis, tmp_path):
        from retrack.reverse.exporters import export_rekordbox_xml

        path = export_rekordbox_xml(project, tmp_path / "out.xml", analysis=analysis)
        root = ET.parse(path).getroot()
        assert root.tag == "DJ_PLAYLISTS"
        track = root.find(".//TRACK")
        assert track is not None
        assert float(track.get("AverageBpm")) == pytest.approx(project.bpm, abs=0.1)
        assert root.findall(".//POSITION_MARK")

    def test_serato_and_mixxx(self, project, analysis, tmp_path):
        from retrack.reverse.exporters import export_mixxx_cues, export_serato_markers

        serato = export_serato_markers(project, tmp_path / "s.serato", analysis=analysis)
        text = serato.read_text(encoding="utf-8")
        assert "GEOB:Serato Markers2" in text
        # Timecodes must carry properly: 59.99 s reads 1:00.00, never 0:60.00.
        assert ":60." not in text

        mixxx = export_mixxx_cues(project, tmp_path / "m.csv", analysis=analysis)
        lines = mixxx.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("file,hotcue")
        assert len(lines) > 1

    def test_recipe_export(self, project, recipe, tmp_path):
        from retrack.reverse.exporters import export_recipe_json

        path = export_recipe_json(project, tmp_path / "r.json", recipe=recipe)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["recipe"]["step_count"] == len(recipe.steps)

    def test_loop_expansion_does_not_drift(self, project):
        """A looped clip must unroll onto the bar grid, not slide off it."""
        from retrack.reverse.exporters.midi import _expand_clip_notes

        looped = next(
            (
                (t, c)
                for t in project.tracks
                for c in t.clips
                if c.loop and c.notes
            ),
            None,
        )
        if looped is None:
            pytest.skip("no looped clips in this reconstruction")
        _track, clip = looped
        notes = _expand_clip_notes(clip, project)
        assert notes
        assert all(clip.start - 1e-6 <= n[0] < clip.end for n in notes)
