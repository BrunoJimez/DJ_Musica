# NOTICE — Third-party components and licenses

RETRACK Studio's own source code is MIT licensed (see [LICENSE](LICENSE)).

The project is designed around a **hard constraint**: *no paid API, no
per-token cost, no proprietary cloud service.* Every analytical capability
either runs locally on your machine or degrades gracefully to a local
algorithm. This file documents every third-party component, its license, and
whether it is required.

## How to read the "Tier" column

| Tier | Meaning |
| --- | --- |
| **core** | Installed by default. Analysis works with only these. |
| **optional** | Enabled by an extra (`pip install -e ".[gui]"`, etc.). Absent → RETRACK falls back to a built-in algorithm and tells you so. |

---

## 1. Core scientific stack

| Component | License | Tier | Used for |
| --- | --- | --- | --- |
| [NumPy](https://numpy.org) | BSD-3-Clause | core | All array math |
| [SciPy](https://scipy.org) | BSD-3-Clause | core | Filtering, signal processing, optimisation |
| [librosa](https://librosa.org) | ISC | core | STFT/CQT, chroma, onsets, HPSS, tempo |
| [soundfile](https://github.com/bastibe/python-soundfile) | BSD-3-Clause | core | libsndfile bindings for audio I/O |
| [libsndfile](http://libsndfile.github.io/libsndfile/) | LGPL-2.1 | core | Bundled by `soundfile` wheels |
| [mido](https://mido.readthedocs.io) | MIT | core | MIDI file writing/reading |
| [Jinja2](https://jinja.palletsprojects.com) | BSD-3-Clause | core | HTML report templating |
| [Matplotlib](https://matplotlib.org) | PSF-based (BSD-compatible) | core | Report figures |
| [Rich](https://github.com/Textualize/rich) | MIT | core | Terminal UI |
| [Typer](https://typer.tiangolo.com) | MIT | core | CLI |
| [platformdirs](https://github.com/platformdirs/platformdirs) | MIT | core | Cross-platform config/cache paths |
| [PyYAML](https://pyyaml.org) | MIT | core | Knowledge-base files |

## 2. Graphical console

| Component | License | Tier | Notes |
| --- | --- | --- | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython/) | **LGPL-3.0** | optional (`[gui]`) | Official Qt binding. LGPL permits use in MIT projects when Qt is dynamically linked (which PySide6 does). Chosen over PyQt6 precisely because PyQt6 is GPL-only for free use. |
| [pyqtgraph](https://www.pyqtgraph.org) | MIT | optional (`[gui]`) | Fast waveform/spectrum plotting |

## 3. Realtime audio and hardware

| Component | License | Tier | Notes |
| --- | --- | --- | --- |
| [sounddevice](https://python-sounddevice.readthedocs.io) | MIT | optional (`[live]`) | PortAudio binding |
| [PortAudio](http://www.portaudio.com) | MIT-like | optional (`[live]`) | WASAPI / ASIO / DirectSound backends |
| [python-rtmidi](https://spotlightkid.github.io/python-rtmidi/) | MIT | optional (`[live]`) | MIDI ports for DJ controllers |
| [RtMidi](https://www.music.mcgill.ca/~gary/rtmidi/) | MIT-like | optional (`[live]`) | Bundled by python-rtmidi |

## 4. Neural models — **all open weights, all local**

| Component | License | Weights license | Tier |
| --- | --- | --- | --- |
| [Demucs / HTDemucs](https://github.com/adefossez/demucs) | MIT | MIT (Meta AI Research) | optional (`[ai]`) |
| [Basic Pitch](https://github.com/spotify/basic-pitch) | Apache-2.0 | Apache-2.0 (Spotify) | optional (`[ai]`) |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | MIT (OpenAI Whisper weights) | optional (`[ai]`) |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT | — | optional (`[ai]`) |
| [ONNX Runtime](https://onnxruntime.ai) | MIT | — | optional (`[ai]`) |
| [PyTorch](https://pytorch.org) | BSD-3-Clause | — | optional (`[ai]`, installed by `scripts/install_torch.py`) |
| [llama.cpp / llama-cpp-python](https://github.com/abetlen/llama-cpp-python) | MIT | depends on GGUF chosen | optional (`[llm]`) |

**Open-weight LLMs suggested by the hardware profiler** (you download them
yourself, none is bundled): Qwen2.5 / Qwen3 family (Apache-2.0), Mistral 7B
(Apache-2.0), Llama 3.x (Meta Llama Community License — free, with
restrictions above 700M MAU), Gemma (Gemma Terms of Use), Phi-3/4 (MIT).
RETRACK prints the license of each candidate before you download it.

## 5. MIR back ends (optional accuracy upgrades)

| Component | License | Tier | Notes |
| --- | --- | --- | --- |
| [madmom](https://github.com/CPJKU/madmom) | **BSD-3-Clause with an academic-use clause** | optional (`[mir]`) | State-of-the-art offline beat/downbeat RNN+DBN. Its license restricts *commercial* redistribution — read it before shipping a commercial product. RETRACK never requires it; the built-in tracker is used by default. |
| [music21](https://github.com/cuthbertLab/music21) | BSD-3-Clause | optional (`[reports]`) | MusicXML score generation |
| [reportlab](https://www.reportlab.com/opensource/) | BSD-3-Clause | optional (`[reports]`) | PDF reports |

## 6. Plugin hosting — **copyleft, read this**

| Component | License | Tier |
| --- | --- | --- |
| [pedalboard](https://github.com/spotify/pedalboard) | **GPL-3.0** | optional (`[plugins]`) |
| [JUCE 6](https://juce.com) (statically linked inside pedalboard) | GPL-3.0 / commercial | optional |
| [Steinberg VST3 SDK](https://github.com/steinbergmedia/vst3sdk) | GPL-3.0 / proprietary | optional |

**Consequence:** if you `pip install "retrack-studio[plugins]"` for your own
use, nothing changes for you. If you **redistribute** a bundle (a PyInstaller
`.exe`, a Docker image, an installer) that includes pedalboard, that bundle
must be GPL-3.0 and you must offer its complete corresponding source. This is
why plugin hosting is an opt-in extra loaded through a thin adapter
(`retrack/plugins/host.py`) rather than a hard dependency.

*VST* is a registered trademark of Steinberg Media Technologies GmbH.
*CLAP* is an open, MIT-licensed plugin standard — prefer it when you can.

## 7. External binaries (not bundled, detected at runtime)

| Tool | License | Used for |
| --- | --- | --- |
| [FFmpeg](https://ffmpeg.org) | LGPL-2.1+ / GPL-2+ depending on build | Decoding formats libsndfile cannot read (mp3/m4a/opus/video) |
| [Chromaprint / `fpcalc`](https://acoustid.org/chromaprint) | LGPL-2.1+ | Optional industry-standard fingerprint alongside RETRACK's built-in one |
| [LilyPond](https://lilypond.org) | GPL-3.0 | Optional high-quality score PDF engraving |

RETRACK calls these as **separate processes** (never links them), which keeps
their licenses out of RETRACK's own license.

## 8. Trademarks and interoperability formats

RETRACK Studio reads and writes several project/library formats to interoperate
with existing tools. It is not affiliated with, endorsed by, or derived from
any of these products, and no proprietary code is used — the exporters are
clean-room implementations based on public documentation and open standards:

- **DAWproject** (Bitwig, MIT-licensed open standard) — the *preferred* export.
- **Reaper** `.rpp` — plain-text, publicly documented.
- **Ableton Live** `.als` — gzipped XML, community-documented. *Ableton Live* is
  a trademark of Ableton AG.
- **rekordbox** XML collection — publicly documented. *rekordbox* and *Pioneer DJ*
  are trademarks of AlphaTheta Corporation.
- **Serato** `GEOB` markers — community-documented. *Serato* is a trademark of
  Serato Audio Research.
- **Mixxx** crates/cues — Mixxx itself is GPL-2.0; RETRACK only writes its
  documented file/DB formats.
- **Traktor** — trademark of Native Instruments GmbH.

## 9. What RETRACK Studio deliberately does NOT use

- No OpenAI / Anthropic / Google / ElevenLabs / any metered API.
- No Spotify / Apple Music / YouTube / SoundCloud content API.
- No Shazam, ACRCloud, Audible Magic or other paid identification service.
- No telemetry, no analytics, no network calls at runtime except:
  1. one-time model downloads you explicitly approve, and
  2. an *optional* AcoustID lookup you must enable and supply your own free
     key for (off by default, and never required).

Run `retrack doctor --licenses` to print this matrix for your actual install.
