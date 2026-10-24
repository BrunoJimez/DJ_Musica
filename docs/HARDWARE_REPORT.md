# Análise do seu PC · Hardware assessment

Medido em 2026-08-01 no computador de destino, com `retrack doctor`.

---

## O que foi encontrado

| Componente | Valor |
|---|---|
| **CPU** | AMD Ryzen 5 4600G — 6 núcleos / 12 threads @ 3,70 GHz |
| **GPU** | **NVIDIA GeForce RTX 4060 — 8 GB GDDR6**, compute 8.9, driver 610.88 |
| **RAM** | 16 GB (15,9 GB utilizáveis) |
| **Disco** | ~90 GB livres de 931 GB |
| **SO** | Windows 10 Pro 19045 (64 bits) |
| **Python** | 3.10, 3.11, 3.13 e 3.14 instalados |
| **Ferramentas** | FFmpeg presente · Git 2.55 · Node 22 |

**Categoria: PERFORMANCE** — assim que o PyTorch com CUDA estiver instalado.
Sem ele, o sistema é classificado como *standard* e usa apenas a CPU.

---

## A conclusão principal

> A RTX 4060 com 8 GB é o componente decisivo desta máquina. Ela coloca você na
> faixa em que **todo o pipeline neural roda localmente e rápido** — separação
> HTDemucs, transcrição Basic Pitch, Whisper large-v3 para letras, e um LLM de
> 7 bilhões de parâmetros quantizado. Um PC sem GPU faz tudo isso também, mas
> 10 a 20 vezes mais devagar.

**A única coisa que falta é instalar a build CUDA do PyTorch:**

```bash
python scripts/install_torch.py
```

Sem isso, a GPU fica ociosa e o programa cai no separador espectral embutido —
funcional, mas com qualidade bem abaixo (~4–5 dB SDR contra ~9 dB).

---

## Como os 8 GB de VRAM são gastos

O RETRACK orça contra **VRAM utilizável**, não total: no Windows, o compositor
do desktop, o navegador e a própria superfície Qt consomem 1 a 1,5 GB. O
orçamento efetivo é de **~6,5 GB**.

| Tarefa | Modelo escolhido | VRAM | Cabe? |
|---|---|---|---|
| Separação | **HTDemucs** (4 camadas) | 3,5 GB | sim, com folga |
| Separação (alta qualidade) | HTDemucs fine-tuned | 7,0 GB | apertado; use se nada mais estiver na GPU |
| Transcrição | **Basic Pitch** | 0,6 GB | sim |
| Letra | **Whisper large-v3** int8_float16 | 4,7 GB | sim |
| Conselheiro | **Qwen2.5 7B Instruct Q4_K_M** | 5,6 GB | sim |
| Conselheiro (maior) | Qwen2.5 14B Q4_K_M | 10,5 GB | não cabe |

**Não rode o Demucs e o LLM ao mesmo tempo.** Somados passam de 9 GB. O RETRACK
serializa os estágios por padrão justamente por isso.

---

## Os 16 GB de RAM

Suficientes, mas é a segunda restrição depois da VRAM. Uma faixa estéreo de
5 minutos a 44,1 kHz ocupa ~100 MB por cópia, e o pipeline mantém a mistura mais
quatro camadas simultaneamente durante a separação — cerca de 2 GB de pico.

Recomendações concretas:

- Feche o navegador antes de analisar sets longos.
- Se algo travar durante a separação, reduza `analysis.demucs_segment` de 7 para 5.
- Para faixas acima de 15 minutos, considere `analysis.max_duration_s`.

---

## Os 6 núcleos

O RETRACK reserva um núcleo físico para a interface e usa **5** para DSP. Isso é
deliberado: com todos os núcleos ocupados, a janela congela e o Windows marca o
processo como "não respondendo".

Para o motor de áudio ao vivo, este processador sustenta confortavelmente um
bloco de **256 amostras** (≈5,8 ms a 44,1 kHz) com 4 decks.

---

## Espaço em disco

90 GB livres. O conjunto completo de modelos ocupa cerca de **12 GB**:

| Item | Tamanho |
|---|---|
| HTDemucs | 0,3 GB |
| HTDemucs fine-tuned | 1,0 GB |
| Basic Pitch | 0,02 GB |
| Whisper large-v3 | 3,1 GB |
| Qwen2.5 7B Q4_K_M | 4,7 GB |
| PyTorch + CUDA | ~2,5 GB |

Mais o cache de análise (~1 MB por faixa) e as camadas renderizadas (~200 MB por
faixa, se você optar por gravá-las).

---

## Áudio

Nove dispositivos de som foram detectados, incluindo dois dispositivos USB e o
FxSound Audio Enhancer. **Nenhum driver ASIO foi encontrado.**

Para tocar em festa:

1. Prefira um dispositivo **WASAPI** na lista da aba *Perform* — latência
   tipicamente 10 a 20 ms.
2. Para beatmatch de ouvido, instale **ASIO4ALL** ou o driver ASIO da sua
   interface. Isso normalmente corta a latência pela metade.
3. Monitoração no fone precisa de **4 saídas** — ou uma controladora com placa
   de som embutida, ou uma segunda interface. Nenhum dos dispositivos atuais
   oferece isso.
4. Desative o FxSound durante apresentações: ele processa a saída e altera o que
   você está ouvindo em relação ao que sai no PA.

---

## Perfil de desempenho estimado

Faixa de 4 minutos, análise completa:

| Configuração | Tempo estimado |
|---|---|
| Hoje (CPU, separador espectral) | ~2 a 3 minutos |
| **Com CUDA + Demucs** | **~40 a 60 segundos** |
| Análise em cache (segunda vez) | < 0,1 segundo |

Medido nesta máquina com o separador espectral: **78 s para 137 s de áudio**
(1,75× tempo real), sendo 28 s de separação e 15 s de análise tonal.

---

## Plano de ação, em ordem

```bash
python scripts/install_torch.py
```

```bash
pip install -e ".[ai]"
```

```bash
retrack doctor
```

Confirme que a linha `GPU` mostra `cuda` e que o plano escolhe `HTDemucs`.
Depois:

```bash
pip install -e ".[gui,live,reports,plugins]"
```

Opcional, para o texto explicativo em português gerado localmente: baixe
`Qwen2.5-7B-Instruct-Q4_K_M.gguf` para a pasta de modelos que o `doctor` mostrou.

---

## Reproduzir esta análise

```bash
retrack doctor --licenses
```

```bash
retrack hardware
```

```bash
retrack models --task separation
```
