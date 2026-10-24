# Guia do usuário · User guide

---

## As dez abas

| Aba | Para quê |
|---|---|
| **Analyse** | Carregar uma faixa e ver tudo que foi medido |
| **Arrange** | O projeto reconstruído, e a exportação |
| **Learn** | Praticar a faixa, estilo Guitar Hero |
| **Perform** | O console de DJ, para tocar |
| **Reports** | Gerar HTML / PDF / Markdown / partitura |
| **Authorship** | Biblioteca de referência e triagem de plágio |
| **AI advisor** | Constatações e orientações |
| **Plugins** | Seus VST3 e as extensões em Python |
| **DJ hardware** | Compatibilidade de controladora e placa de som |
| **System** | Perfil da máquina e plano de modelos |

---

## Fluxo típico

### 1. Analisar

Abra uma faixa em **Analyse**. A primeira análise leva de um a três minutos; o
resultado fica em cache pelo conteúdo do arquivo, então reabrir é instantâneo.

Leia os oito blocos no topo: andamento, tonalidade, compasso, duração, loudness,
groove, gênero e energia. A forma de onda abaixo mostra as seções coloridas por
função, a grade de compassos e os pontos de mixagem.

**Confie nos rótulos de confiança.** "medium" numa tonalidade significa que o
programa não tem certeza, e normalmente é porque a faixa é modal ou tem pouca
harmonia.

### 2. Ver como foi feita

Vá para **Arrange**. Cada camada vira uma faixa; cada seção vira um clipe;
material repetido vira um loop. A árvore embaixo lista os dispositivos
inferidos com a **evidência** de cada um — passe o mouse para ler.

O painel da direita diz o que a reconstrução **não** pode saber. Leia uma vez.

### 3. Exportar

Escolha o formato e clique em **Export**.

**Use DAWproject se puder.** É o único formato aberto que leva as cadeias de
dispositivos junto com as notas — Bitwig e Studio One abrem direto. MIDI leva a
música mas perde os efeitos. Ableton leva as faixas mas os dispositivos vão para
as anotações (o formato de dispositivo do Live é travado por versão e um nó
malformado faz o Live recusar o arquivo inteiro).

### 4. Aprender a refazer

Em **Learn**, as aulas aparecem em ordem, com travas: você abre a próxima ao
atingir 80% na atual.

Comece a 75% do andamento. As janelas de tempo **escalam com a velocidade** —
tocar devagar é mais fácil de verdade, não só mais lento. Suba para 90% e depois
100% conforme acertar.

Teclas **A S D F G** batem nas faixas 1 a 5, ou clique nelas.

Ao terminar, leia o retorno. Ele distingue duas coisas diferentes:

- *"você está 18 ms adiantado"* — um viés. Você está reagindo em vez de contar.
- *"seu tempo varia 50 ms"* — dispersão. Diminua o andamento até fechar.

### 5. Tocar

**Perform** é o console. Escolha a saída, clique em **Start audio**.

Ordem importa numa festa:

1. Escolha um dispositivo **WASAPI** (Windows) ou **ASIO** se tiver.
2. Verifique a latência no rodapé. Acima de 20 ms não dá para beatmatch de
   ouvido.
3. Carregue os decks **antes** de começar — a análise leva tempo.
4. **PANIC** para tudo. Está sempre visível por isso.

Os hot cues já vêm posicionados nos pontos musicais que a análise encontrou:
o drop, os pontos de entrada e saída, e cada início de seção.

---

## Linha de comando

Tudo funciona sem interface.

```bash
retrack doctor
```

```bash
retrack analyze "faixa.wav"
```

```bash
retrack report "faixa.wav" --out relatorios --lang pt_BR --authorship
```

```bash
retrack export "faixa.wav" --formats all --out exports
```

```bash
retrack learn "faixa.wav" --step 3
```

```bash
retrack setlist "pasta/do/set" --shape arc
```

```bash
retrack library add "pasta/referencias"
```

```bash
retrack authorship "faixa.wav"
```

---

## Interpretando os resultados

### Andamento e grade

Um `is_constant_tempo` verdadeiro significa que a faixa foi produzida numa
grade fixa. Falso significa que a grade deriva — e os números de compasso perto
do fim são aproximados.

`groove_deviation_ms` abaixo de 6 ms significa quantização total. Acima de 20 ms
significa tocado ou humanizado de propósito.

### Tonalidade

O código Camelot é o que importa para mixar. `8A` combina com `8A`, `9A`, `7A` e
`8B`. Fora disso, use EQ para esconder ou mixe numa parte percussiva.

Se a afinação estiver muito longe de 440 Hz, a faixa foi acelerada ou afinada de
propósito — e qualquer coisa que você tocar por cima em 440 vai bater contra.

### Camadas

A participação é calculada por **loudness**, não por energia bruta, porque
energia é dominada pelo sub-grave e reportaria "bateria 75%, resto 0,3%" numa
mistura onde o pad é claramente audível.

Se a linha do backend disser `separation=spectral`, você está no separador
embutido. Instale `[ai]` e o torch com CUDA — a diferença é grande.

### Design sonoro

A confiança é limitada a 65% de propósito. São hipóteses que reproduzem o que se
ouve, não configurações recuperadas. Use como ponto de partida.

### Originalidade

Sempre relativa à biblioteca que você montou. Leia [LEGAL.md](LEGAL.md).

---

## Atalhos

| Tecla | Ação |
|---|---|
| `Ctrl+O` | Abrir faixa |
| `Ctrl+E` | Exportar projeto |
| `Ctrl+R` | Gerar relatório |
| `Ctrl+1`…`Ctrl+9` | Ir para a aba |
| `F11` | Modo palco |
| `A S D F G` | Faixas do highway (aba Learn) |

---

## Configurações

O arquivo `settings.toml` fica na pasta que o `retrack doctor` reporta. Apagá-lo
restaura os padrões. Chaves desconhecidas são preservadas, então uma versão nova
não destrói um campo futuro.

Ajustes que valem conhecer:

```toml
[analysis]
separation_backend = "demucs"   # ou "spectral" para forçar o embutido
demucs_segment = 5              # reduza se faltar memória
chord_vocabulary = "sevenths"   # ou "triads" para simplificar

[audio]
block_size = 256                # menor = menos latência, mais CPU

[learn]
window_perfect_ms = 35.0        # aperte para treinar precisão
```
