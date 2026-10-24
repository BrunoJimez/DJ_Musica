# Guia de instalação · Installation guide

> Português primeiro; English follows each section.

---

## 1. Requisitos

| Item | Mínimo | Recomendado |
|---|---|---|
| Python | 3.10 | **3.11 ou 3.12** |
| RAM | 4 GB | 16 GB |
| CPU | 2 núcleos | 6+ núcleos |
| GPU | nenhuma | NVIDIA com 6+ GB VRAM |
| Disco | 2 GB | 20 GB (com todos os modelos) |
| SO | Windows 10+, macOS 11+, Linux | — |

**Por que 3.11/3.12 e não 3.13+:** `librosa` depende de `numba`, que costuma
demorar alguns meses para suportar cada Python novo. Se `pip install librosa`
falhar, é quase sempre isso. Use 3.11 ou 3.12 e o problema desaparece.

*Python 3.11 or 3.12 is recommended. `librosa` depends on `numba`, which lags
new Python releases by a few months.*

---

## 2. Instalação passo a passo

### Windows

```powershell
git clone https://github.com/BrunoJimez/retrack-studio.git
```

```powershell
cd retrack-studio
```

```powershell
py -3.11 -m venv .venv
```

```powershell
.venv\Scripts\Activate.ps1
```

Se o PowerShell recusar o script de ativação:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

```powershell
python -m pip install --upgrade pip
```

```powershell
pip install -e ".[gui,live,reports]"
```

### macOS / Linux

```bash
git clone https://github.com/BrunoJimez/retrack-studio.git && cd retrack-studio
```

```bash
python3.11 -m venv .venv && source .venv/bin/activate
```

```bash
pip install --upgrade pip && pip install -e ".[gui,live,reports]"
```

No Linux, o PortAudio precisa das bibliotecas do sistema:

```bash
sudo apt install portaudio19-dev libsndfile1 ffmpeg
```

---

## 3. Verifique a instalação

```bash
retrack doctor
```

Este comando é o ponto de partida. Ele mostra:

- o perfil de hardware da sua máquina e a categoria em que ela cai;
- cada componente opcional: presente ou ausente, **o que ele habilita**, **qual
  é o plano B** e **como instalá-lo**;
- qual modelo gratuito foi escolhido para cada tarefa e por quê.

*Run this first. It reports what is installed, what each missing component
would enable, what RETRACK falls back to without it, and the exact install
command.*

---

## 4. Extras opcionais

Instale só o que você for usar.

| Extra | Comando | O que ganha |
|---|---|---|
| Interface gráfica | `pip install -e ".[gui]"` | O console completo |
| Áudio ao vivo | `pip install -e ".[live]"` | Reprodução, decks, controladoras MIDI |
| Relatórios | `pip install -e ".[reports]"` | PDF e partitura MusicXML |
| Modelos neurais | `pip install -e ".[ai]"` | Demucs, Basic Pitch, Whisper |
| Plugins VST3 | `pip install -e ".[plugins]"` | Hospedar seus VST3/CLAP/AU |
| MIR avançado | `pip install -e ".[mir]"` | Rastreador de beats do madmom |
| LLM local | `pip install -e ".[llm]"` | Texto explicativo gerado localmente |

Tudo de uma vez (exceto torch, que tem passo próprio):

```bash
pip install -e ".[gui,live,reports,ai,plugins,mir,llm]"
```

### Avisos de licença

- **`[plugins]`** puxa o `pedalboard`, que é **GPL-3.0**. Usar na sua máquina não
  muda nada. **Redistribuir** um pacote que o inclua torna o pacote GPL.
- **`[mir]`** puxa o `madmom`, cuja licença tem uma cláusula de uso acadêmico.
  Leia antes de usar comercialmente.

Detalhes completos: [../NOTICE.md](../NOTICE.md).

---

## 5. FFmpeg

Sem FFmpeg, o RETRACK lê apenas WAV, FLAC, OGG e AIFF. **Com** ele, lê MP3, M4A,
AAC, WMA, Opus e o áudio de arquivos de vídeo.

```powershell
winget install Gyan.FFmpeg
```

```bash
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Debian/Ubuntu
```

Feche e reabra o terminal depois de instalar, para o PATH atualizar.

---

## 6. Aceleração por GPU (NVIDIA)

Isto é o que transforma a separação de camadas de "lenta mas funcional" em
"quase instantânea" — tipicamente **10 a 20 vezes mais rápido**.

```bash
python scripts/install_torch.py
```

O script detecta a sua GPU e instala a build correta do PyTorch. Ou manualmente:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Confirme:

```bash
retrack doctor
```

A linha `GPU` deve mostrar o backend `cuda`, e o plano de modelos deve escolher
`HTDemucs` em vez do separador espectral embutido.

*Skip this if you have no NVIDIA GPU. Everything still works on CPU — slower,
and the built-in spectral separator is used instead of Demucs.*

---

## 7. Modelo de linguagem local (opcional)

O motor de regras produz **todas** as constatações e todos os números sem
nenhum modelo. Um LLM local só reescreve isso em prosa corrida.

1. Veja qual modelo cabe na sua máquina:

```bash
retrack models --task llm
```

2. Baixe um arquivo `.gguf` (por exemplo, do Hugging Face) para a pasta de
   modelos que o `retrack doctor` mostrou.
3. O RETRACK encontra sozinho na próxima execução.

Sugestões por VRAM disponível:

| VRAM utilizável | Modelo | Licença |
|---|---|---|
| 12 GB+ | Qwen2.5 14B Instruct Q4_K_M | Apache-2.0 |
| 6–8 GB | **Qwen2.5 7B Instruct Q4_K_M** | Apache-2.0 |
| 4–6 GB | Mistral 7B Instruct v0.3 Q4_K_M | Apache-2.0 |
| 3–4 GB | Phi-4 mini Q4_K_M | MIT |
| CPU apenas | Qwen2.5 3B Instruct Q4_K_M | Qwen Research |

---

## 8. Problemas comuns

**`ModuleNotFoundError: numba` ou falha ao instalar librosa**
Sua versão do Python é nova demais. Crie o ambiente com 3.11 ou 3.12.

**`retrack: command not found`**
O ambiente virtual não está ativo. Ative-o, ou use `python -m retrack`.

**A interface não abre**
`pip install -e ".[gui]"`. No Linux headless, defina `QT_QPA_PLATFORM=offscreen`
para os testes, ou instale um servidor gráfico.

**Sem saída de áudio / "could not open the audio device"**
`pip install -e ".[live]"`. No Windows, prefira um dispositivo **WASAPI** na
lista da aba Perform. Latência acima de 20 ms inviabiliza beatmatch de ouvido —
instale ASIO4ALL ou o driver ASIO da sua interface.

**A separação de camadas está péssima**
Você está no separador espectral embutido. `pip install -e ".[ai]"` e depois
`python scripts/install_torch.py`. O `retrack doctor` confirma a mudança.

**A análise demora muito**
Normal na primeira vez. O resultado fica em cache pelo conteúdo do arquivo —
a segunda análise do mesmo arquivo é instantânea. Use `--no-cache` para forçar.

**Erro de memória durante a separação**
Reduza `analysis.demucs_segment` em `settings.toml` (o `retrack doctor` mostra
o caminho), ou force o separador embutido com
`analysis.separation_backend = "spectral"`.

---

## 9. Desinstalar

```bash
pip uninstall retrack-studio
```

Os dados do usuário (cache, biblioteca de referência, configurações) ficam na
pasta que o `retrack doctor` reporta. Apague-a para remover tudo.
