# Hardware de DJ · DJ hardware

```bash
retrack hardware
```

Ou abra a aba **DJ hardware**. O relatório lista cada porta MIDI, o que o
RETRACK reconhece nela, e o que vai funcionar.

---

## Como o suporte funciona

O RETRACK fala **MIDI genérico**, que é o que a esmagadora maioria das
controladoras envia. Um mapeamento é um arquivo JSON dizendo o que cada
controle faz. Alguns mapeamentos vêm com o programa, uma controladora
desconhecida cai no mapeamento genérico, e o **MIDI learn** deixa você atribuir
qualquer coisa tocando nela.

### Níveis de suporte

| Nível | Significa |
|---|---|
| **good** | Transporte, EQ, faders, loops e cues funcionam por MIDI padrão |
| **partial** | Parte dos controles usa HID em vez de MIDI, ou é proprietária |
| **basic** | Não está no banco de dados; o mapeamento genérico é usado |

Os níveis descrevem o que um host **MIDI genérico** consegue fazer — não o que o
software do fabricante faz.

---

## Controladoras reconhecidas

| Modelo | Protocolo | Nível | Observação |
|---|---|---|---|
| Pioneer DDJ-FLX4 | MIDI + áudio | good | Class-compliant no Windows |
| Pioneer DDJ-400 / SB3 / 200 | MIDI + áudio | good | Jog wheels em CC relativo |
| Pioneer DDJ-1000 / 800 / REV | MIDI + áudio | partial | Displays dos jogs ficam apagados |
| Pioneer CDJ-2000NXS2 / 3000 | MIDI | partial | PRO DJ LINK é proprietário |
| NI Traktor Kontrol S2 / S3 | MIDI + áudio | partial | **Coloque em modo MIDI** no Controller Editor |
| NI Kontrol X1 / F1 | MIDI | good | LEDs funcionam |
| Numark Mixtrack / Party Mix | MIDI + áudio | good | Sem drivers |
| Hercules DJControl | MIDI + áudio | good | Sem drivers |
| Denon MC7000 / MC4000 / Prime | MIDI + áudio | good | Modo controladora |
| Reloop | MIDI + áudio | good | — |
| Akai APC / MPD | MIDI | good | Pads viram hot cues e faixas do highway |
| Novation Launchpad / Launchkey | MIDI | good | Grade + feedback de LED |

**A sua não está aqui?** Provavelmente funciona mesmo assim. Conecte, rode
`retrack hardware`, e use o MIDI learn para o que não cair no lugar.

---

## O mapeamento genérico

Segue a convenção que quase todo fabricante usa: **um canal MIDI por deck**,
transporte em notas, controles contínuos nos CCs baixos.

### Por deck (canal = número do deck)

| Controle | Tipo | Número |
|---|---|---|
| Play / pause | nota | `0x0B` |
| Cue | nota | `0x0C` |
| Sync | nota | `0x58` |
| Keylock | nota | `0x0D` |
| Loop 1 / 2 / 4 / 8 | nota | `0x10`–`0x13` |
| Sair do loop | nota | `0x14` |
| Metade / dobro | nota | `0x15` / `0x16` |
| Hot cues 1–8 | nota | `0x20`–`0x27` |
| Pitch | CC | `0x00` |
| Volume | CC | `0x07` |
| EQ agudo / médio / grave | CC | `0x0F` / `0x0B` / `0x17` |
| Filtro | CC | `0x1A` |
| Trim | CC | `0x04` |
| Jog (relativo) | CC | `0x21` |

### Globais (canal 15)

| Controle | Tipo | Número |
|---|---|---|
| Crossfader | CC | `0x08` |
| Master | CC | `0x09` |
| Mix do fone | CC | `0x0A` |
| Navegar (relativo) | CC | `0x64` |
| Carregar no deck | nota | `0x46` |
| Gravar | nota | `0x48` |
| **Pânico** | nota | `0x7F` |

### Aprendizado (canal 10)

Faixas 1 a 5 do highway em `0x24`–`0x28` — a mesma região que pads de bateria
usam por convenção GM.

---

## Encoders relativos

Não existe padrão para isto, e é por isso que jog wheels se comportam de forma
estranha em software que assume uma única codificação. O RETRACK suporta as
três que cobrem quase tudo:

| Estilo | Codificação |
|---|---|
| `twos_complement` | 1–63 para frente, 65–127 para trás (Pioneer, maioria) |
| `binary_offset` | Centrado em 64 |
| `signed_bit` | Bit 6 é direção, bits baixos são magnitude |

---

## Áudio

### Latência

| API | Latência típica | Recomendação |
|---|---|---|
| **ASIO** | 3–10 ms | Melhor opção no Windows |
| **WASAPI** | 10–20 ms | Bom padrão, sem drivers |
| DirectSound | 30–60 ms | Evite |
| MME | 60–150 ms | Não use para tocar |

Acima de **20 ms** não dá para beatmatch de ouvido. Se você não tem interface
com driver ASIO próprio, o **ASIO4ALL** normalmente corta a latência pela metade.

O tamanho de bloco também importa. O RETRACK sugere um valor com base no seu
processador:

| CPU | Bloco sugerido | Latência a 44,1 kHz |
|---|---|---|
| 8+ núcleos, 16 GB+ | 256 | ~5,8 ms |
| 4+ núcleos | 512 | ~11,6 ms |
| Menos | 1024 | ~23 ms |

### Monitoração no fone

Precisa de **4 saídas**: duas para o master, duas para o fone. As opções:

1. Uma controladora com placa de som embutida (a maioria tem).
2. Uma interface com 4+ saídas.
3. Sem isso, você toca sem pré-escuta — use os pontos de mixagem que a análise
   marcou.

O `retrack hardware` diz se algum dispositivo seu tem 4 saídas.

---

## Antes de tocar numa festa

Uma checagem que vale os cinco minutos:

1. `retrack hardware` — confirme controladora e saída.
2. Analise **todas** as faixas com antecedência. A análise leva tempo; o cache
   torna o carregamento instantâneo depois.
3. Teste o **PANIC**.
4. Ligue a gravação (`● REC`) — você vai querer ouvir depois.
5. Desative qualquer "melhorador de áudio" do sistema. Ele processa a saída e o
   que você ouve deixa de ser o que vai para o PA.
6. Desative suspensão automática e atualizações do sistema.
7. Leve a faixa em WAV ou FLAC. MP3 de 128 kbps perde tudo acima de 16 kHz, e
   num sistema grande isso se ouve.
