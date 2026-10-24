<div align="center">

# RETRACK Studio

**Engenharia reversa de faixas · Aprendizado de produção · Console de DJ ao vivo**

*Reverse engineer the track. Learn how it was built. Play it live.*

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10--3.13-blue.svg)](https://www.python.org)
[![100% offline](https://img.shields.io/badge/APIs%20pagas-nenhuma-brightgreen.svg)](NOTICE.md)

</div>

---

> **English:** RETRACK Studio takes a finished audio file and works *backwards* —
> recovering the tempo grid, key, chords, arrangement, instrument layers, effect
> chains and mix decisions, then rebuilding all of it as an editable project you
> can inspect, learn from, perform with and export. It runs entirely on your own
> machine. There is no paid API, no metered token, no telemetry. Full English
> documentation lives in [`docs/`](docs/).

## O que é

Você fez uma faixa há seis meses e não lembra mais como chegou naquele som.
Ou ouviu uma música e quer entender como ela foi construída, camada por camada.
O RETRACK pega o arquivo de áudio **pronto** e trabalha de trás para frente:

- Recupera o **andamento**, a **grade de compassos**, a **tonalidade** e a **progressão harmônica**
- Separa as **camadas** (bateria, baixo, harmonia, vocais)
- Transcreve as **notas** e o **padrão de bateria**
- Deduz a **cadeia de efeitos**, o **sidechain** e as decisões de **masterização**
- Reconstrói tudo como um **projeto editável** — e exporta para o seu DAW
- Ensina **passo a passo** como refazer a faixa, no estilo Guitar Hero
- Toca ao vivo num **console de DJ completo** para você usar na festa

É como um programa de aprender inglês, mas para produção musical: pega algo
pronto, mostra as peças, e te ensina a fazer de novo.

## Restrição de projeto: livre e offline

Isto não é um detalhe de implementação — é a regra que moldou o programa inteiro:

- **Nenhuma API paga.** Nenhum token, nenhuma cobrança por uso, nunca.
- **Nenhum serviço de nuvem.** Nada do seu áudio sai da máquina.
- **Modelos de pesos abertos apenas** (Demucs MIT, Basic Pitch Apache-2.0,
  Whisper MIT, Qwen/Mistral/Phi Apache-2.0 ou MIT).
- **Tudo degrada com elegância.** Sem GPU, sem torch, sem downloads? Todo estágio
  neural tem um caminho clássico de DSP embutido, e o programa te diz qual usou.

Veja [NOTICE.md](NOTICE.md) para a matriz completa de licenças.

---

## Telas

| Analisar | Arranjo reconstruído |
|---|---|
| Forma de onda com seções, grade e cues; BPM, tonalidade, groove, gênero | Cada faixa, clipe, dispositivo e automação que a análise conseguiu inferir |

| Aprender | Tocar |
|---|---|
| Autoestrada de notas estilo Guitar Hero, com plano de aulas e correção de tempo | 2–4 decks, EQ de 3 bandas, filtro, crossfader, loops, hot cues, gravação |

---

## Instalação rápida

```bash
git clone https://github.com/BrunoJimez/retrack-studio.git
```

```bash
cd retrack-studio && python -m venv .venv && .venv\Scripts\activate
```

```bash
pip install -e ".[gui,live,reports]"
```

```bash
retrack doctor
```

`retrack doctor` inspeciona o seu PC e diz exatamente o que está disponível, o
que falta, e qual modelo gratuito cabe na sua máquina. **Rode isso primeiro.**

Guia completo, incluindo FFmpeg e aceleração por GPU:
**[docs/INSTALL.md](docs/INSTALL.md)**

## Primeiro uso, sem baixar nada

O programa gera a própria faixa de demonstração — livre de direitos, com a
verdade conhecida (128 BPM, Lá menor, estrutura documentada):

```bash
retrack demo
```

```bash
retrack analyze examples/generated/retrack_demo_techhouse.wav
```

```bash
retrack gui
```

---

## Como usar

### Análise e relatórios

```bash
retrack analyze "minha_faixa.wav"
```

```bash
retrack report "minha_faixa.wav" --out relatorios --lang pt_BR
```

Gera HTML autocontido (todos os gráficos embutidos), PDF, Markdown, JSON e
partitura MusicXML — com letra transcrita, cifra, tablatura de bateria,
diagnóstico de mixagem e receita de construção.

### Exportação para DAW e DJ

```bash
retrack export "minha_faixa.wav" --formats all --out exports
```

| Formato | O que leva |
|---|---|
| **DAWproject** | Faixas, clipes, notas, automação **e cadeias de dispositivos** — o mais completo |
| MIDI | Todas as partes e a bateria, tipo 1 multitrilha |
| Reaper `.rpp` | Projeto em texto puro, inspecionável |
| Ableton `.als` | Faixas MIDI, clipes, locators (dispositivos vão nas anotações) |
| rekordbox XML | Beat grid, tonalidade, hot cues nos pontos musicais |
| Serato / Mixxx | Marcadores e cues |
| JSON | Tudo, legível por máquina |

### Aprender a refazer a faixa

```bash
retrack learn "minha_faixa.wav" --difficulty beginner
```

Ou abra a aba **Learn** na interface: plano de aulas com travas de progressão,
autoestrada de notas, rampa de andamento (75% → 90% → 100%) e correção
específica — *"você está 18 ms adiantado; conte o tempo antes da nota"*.

### Autoria e plágio

```bash
retrack library add "pasta/com/suas/referencias"
```

```bash
retrack authorship "minha_faixa.wav"
```

Impressão digital acústica própria (constelação de picos, estilo Shazam) mais
comparação **melódica, harmônica, rítmica, tímbrica e estrutural**. O resultado é
sempre **relativo à biblioteca que você montou** — e o relatório diz isso em
letras grandes. Leia [docs/LEGAL.md](docs/LEGAL.md) antes de usar isso para
qualquer coisa séria.

### Set de DJ

```bash
retrack setlist "pasta/do/set" --shape arc
```

Ordena as faixas por compatibilidade de andamento e tonalidade (roda Camelot),
desenhando uma curva de energia.

---

## O que ele mede, e com que confiança

Cada estimativa carrega um valor de confiança e o nome do método que a produziu.
Validado contra a faixa sintética de verdade conhecida:

| Medida | Resultado |
|---|---|
| BPM | erro < 0,005 BPM em 124–174 BPM |
| Posição dos beats | erro mediano 1–5 ms |
| Downbeats | 100% dentro de 70 ms |
| Tonalidade | 4/4 corretas, com Camelot correto |
| Progressão harmônica | exata (`Am Dm C Em`) |
| Fronteiras de seção | exatas (compassos 1, 9, 17, 33, 41, 49, 65) |
| Swing | 0,613 medido vs 0,62 real |
| Loudness | conforme ITU-R BS.1770-4 (±0,01 LU no teste de conformidade) |

Rode você mesmo: `pytest tests/ -v`

---

## Arquitetura

```
retrack/
├── system/       perfil de hardware, matriz de capacidades, escolha de modelos
├── audio/        E/S, DSP, medição de loudness (BS.1770), motor de tempo real
├── analysis/     ritmo · tonal · estrutura · separação · bateria ·
│                 transcrição · timbre · mixagem · design sonoro · letra
├── reverse/      modelo de projeto, construtor, receita, 9 exportadores
├── authorship/   impressão digital, similaridade, banco de referência, originalidade
├── ai/           motor de regras determinístico + LLM local opcional
├── learn/        autoestrada de notas, plano de aulas, correção
├── live/         decks, mixer, sincronismo, gravação, planejador de set
├── hardware/     MIDI, mapeamentos de controladora, compatibilidade
├── plugins/      host VST3/CLAP/AU + API de extensão em Python
├── reports/      HTML · PDF · Markdown · JSON · gráficos
└── ui/           console gráfico (PySide6)
```

Detalhes em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). A base científica, com
referências, em [docs/SCIENTIFIC_BASIS.md](docs/SCIENTIFIC_BASIS.md).

## Estendendo

Coloque um `.py` na pasta de plugins:

```python
from retrack.plugins import RetrackPlugin

class MinhaAnalise(RetrackPlugin):
    name = "Afinador de bumbo"
    category = "analysis"

    def provide_insights(self, analysis):
        return []
```

Veja [docs/PLUGINS.md](docs/PLUGINS.md).

---

## Honestidade sobre limites

O programa reconstrói **o que pode ser medido**, não a sessão original.
Escolhas de instrumento, ajustes exatos de plugin e roteamento **não são
recuperáveis** de uma mixagem final — muitos patches diferentes produzem
espectros indistinguíveis. Por isso:

- a confiança do design sonoro é limitada a 65% por construção;
- cada dispositivo inferido mostra a **evidência** que o gerou;
- o relatório abre com uma seção dizendo o que ele não é;
- a análise de autoria nunca afirma violação, apenas mede similaridade.

Sem separação neural (Demucs), a classificação de bateria e a transcrição
pioram de forma perceptível — o programa avisa quando isso acontece.

## Contribuir

[CONTRIBUTING.md](CONTRIBUTING.md) · [CHANGELOG.md](CHANGELOG.md) ·
[Código de conduta](CODE_OF_CONDUCT.md)

## Licença

MIT para o código do RETRACK. Componentes opcionais têm licenças próprias —
alguns copyleft. **Leia [NOTICE.md](NOTICE.md) antes de redistribuir um pacote.**

<div align="center">
<sub>Construído para quem quer entender música, não só consumi-la.</sub>
</div>
