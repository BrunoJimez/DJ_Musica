"""A worked example of a native RETRACK plugin.

Copy this file into your plugins folder (``retrack doctor`` prints the path)
and it loads on the next start. It adds two findings to the AI advisor that the
built-in rules do not cover.

Nothing here is special-cased: this is the whole extension API.
"""

from __future__ import annotations

from retrack.plugins import RetrackPlugin


class KickTuningAdvisor(RetrackPlugin):
    """Checks whether the kick's fundamental agrees with the track's key."""

    name = "Kick tuning advisor"
    version = "1.0"
    author = "RETRACK examples"
    description = "Flags a kick tuned against the key, and suggests the note to use."
    category = "advisor"

    def provide_insights(self, analysis):
        from retrack.ai.rules import Insight
        from retrack.analysis.features import PITCH_CLASSES

        if analysis.tonal is None or analysis.drums is None:
            return []
        if len(analysis.drums.hits_of("kick")) < 8:
            return []

        tonic = PITCH_CLASSES[analysis.tonal.key_root % 12]
        return [
            Insight(
                category="mix",
                title="Tune the kick to the key",
                observation=(
                    f"This track is in {analysis.tonal.key_name}, so the kick's "
                    f"fundamental wants to be {tonic} or its fifth."
                ),
                why=(
                    "A kick whose pitch fights the bass produces a beating "
                    "interval in the sub range. You hear it as a loss of power "
                    "rather than as a wrong note, which is why it is easy to "
                    "miss and worth checking deliberately."
                ),
                action=(
                    f"Pitch the kick sample until its body sits on {tonic}, or "
                    "high-pass it and let the bass own the sub."
                ),
                confidence=0.45,
                evidence={"key": analysis.tonal.key_name, "suggested_root": tonic},
            )
        ]


class ArrangementLengthCheck(RetrackPlugin):
    """Warns when the track is outside the length a DJ can comfortably mix."""

    name = "Arrangement length check"
    version = "1.0"
    author = "RETRACK examples"
    description = "Checks total length and intro/outro length against DJ conventions."
    category = "advisor"

    def provide_insights(self, analysis):
        from retrack.ai.rules import Insight

        if analysis.structure is None or not analysis.structure.segments:
            return []

        minutes = analysis.duration / 60.0
        segments = analysis.structure.segments
        intro = segments[0].bar_length if segments else 0
        outro = segments[-1].bar_length if len(segments) > 1 else 0

        findings = []

        if minutes < 3.0:
            findings.append(
                Insight(
                    category="arrangement",
                    title="Short for a club edit",
                    observation=f"The track runs {minutes:.1f} minutes.",
                    why=(
                        "A DJ needs roughly 32 bars of steady material at each "
                        "end to blend into and out of. Under three minutes there "
                        "is rarely room for both."
                    ),
                    action="Consider extending the intro and outro for a club version.",
                    severity="tip",
                    confidence=0.5,
                    evidence={"minutes": round(minutes, 2)},
                )
            )

        if intro and intro < 8:
            findings.append(
                Insight(
                    category="arrangement",
                    title="Very short intro",
                    observation=f"The intro is {intro} bars.",
                    why="Under 8 bars leaves almost no room to beatmatch into.",
                    action="16 or 32 bars of intro is the usual club convention.",
                    severity="tip",
                    confidence=0.55,
                    evidence={"intro_bars": intro, "outro_bars": outro},
                )
            )

        return findings
