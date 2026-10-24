# Base científica · Scientific basis

Cada estágio da análise, o método escolhido, por que ele foi escolhido, e a
literatura que o sustenta. Onde o RETRACK se afasta da prática comum, o motivo
está registrado.

*Every analysis stage, the method chosen, why, and the literature behind it.*

---

## 1. Panorama da área

Recuperação de Informação Musical (MIR) amadureceu ao ponto de várias tarefas
terem soluções de código aberto competitivas com produtos comerciais. O estado
da arte em 2026, para o que este programa precisa:

| Tarefa | Referência aberta | Nível |
|---|---|---|
| Beats / downbeats | madmom (RNN+DBN), BeatNet (CRNN + filtro de partículas) | maduro |
| Separação de fontes | HTDemucs (~9,0 dB SDR vocal), BS-RoFormer | maduro |
| Estrutura | All-In-One (Kim & Nam, ISMIR 2023) | bom |
| Transcrição | Basic Pitch (Spotify), MT3, MuScriptor | bom |
| Tonalidade | perfis de classe de altura + variantes | maduro |
| Acordes | template matching + decodificação temporal | bom |
| Letra | Whisper (fala; canto degrada) | parcial |
| Identificação | Chromaprint / constelação de picos | maduro |

O RETRACK usa esses componentes quando estão instalados e implementa
alternativas clássicas quando não estão — sempre dizendo qual caminho usou.

---

## 2. Ritmo: andamento, beats, downbeats

### Detecção de onsets

Fluxo espectral multibanda sobre log-magnitude, com filtro de máximo ao longo da
frequência para suprimir vibrato. Formulação de **Böck & Widmer, "Maximum filter
vibrato suppression for onset detection", DAFx-12**.

Cada banda é normalizada **antes** da fusão. Sem isso, o sub-grave domina e um
chimbal deixa de contribuir.

### Andamento

Autocorrelação do envelope de onsets, ponderada por um prior log-normal centrado
em **124 BPM** (e não nos 120 usuais — a massa da música de clube está entre 120
e 140), combinada com um escore de filtro pente.

O filtro pente é o que resolve a ambiguidade de oitava: no andamento verdadeiro
a energia cai em **todos** os pulsos; na metade, apenas em pulsos alternados.

**Correção de oitava explícita.** Abaixo de 95 BPM, o programa mede se os pulsos
intermediários têm energia comparável. Se têm, o andamento real é o dobro. Foi
isso que corrigiu drum & bass de 174 BPM sendo reportado como 87.

### Rastreamento de beats

Programação dinâmica de **Ellis, "Beat tracking by dynamic programming",
J. New Music Research 36(1), 2007**, com penalidade log-gaussiana sobre o desvio
do período. A rigidez (`tightness=340`) é alta porque música eletrônica é de fato
quantizada; para material tocado ao vivo, ~100 seria mais adequado.

### Ajuste do período — decisão não óbvia

`median(diff(beats))` é a forma óbvia de obter o período, **e mede errado**.
Com beats resolvidos a ~11 ms, intervalos consecutivos alternam entre contagens
de frame vizinhas e a mediana trava numa delas — a 128 BPM, um erro de ~1,2 BPM.

O RETRACK regride tempo contra **índice de beat** ao longo da faixa inteira,
atribuindo índices de forma incremental (arredondando cada intervalo
separadamente) para que um beat perdido não distorça o ajuste. Isso levou o erro
de 1,199 BPM para **0,001 BPM**.

### Viés sistemático do onset — decisão não óbvia

Uma STFT centrada reporta onsets **adiantados**: a janela que primeiro contém o
transiente está centrada até meia janela antes dele. Com `n_fft=2048`, o pico de
fluxo antecede o ataque real em cerca de 10 ms.

Isso é invisível em métricas de beat tracking (tolerância de 70 ms) mas é *o
sinal inteiro* na análise de groove, onde se medem desvios de poucos
milissegundos. Cada candidato é reexaminado na forma de onda a 16 amostras de
resolução e movido para o ponto de subida mais íngreme de energia.

### Swing

Medido **apenas nos chimbais** (banda superior). Swing vive na percussão; bumbo,
baixo e stabs ficam retos, e uma mediana sobre todos os onsets é puxada de volta
para 0,5 pela maioria não-swingada.

E medido por **densidade kernel, não histograma**: a população real é *larga*
(espalhada por jitter), enquanto um agrupamento espúrio pode ser estreito o
bastante para vencer um `argmax` de histograma. Reto é a hipótese nula — uma
leitura swingada precisa superá-la por margem clara.

---

## 3. Tonalidade e harmonia

### Afinação primeiro

Tudo depende dos bins de croma coincidirem com semitons reais. Uma faixa
acelerada ou afinada em 432 Hz borra os bins. A referência é medida antes.

### CQT, não FFT

Uma STFT linear dá ~1 bin por semitom em 250 Hz e ~30 bins por semitom em 8 kHz
— o grave, onde vive a fundamental, é o pior resolvido. A transformada Q
constante dá resolução igual por oitava.

### O filtro passa-altas antes do croma — decisão não óbvia

Um bumbo **não** é percussivo no sentido do HPSS: seu corpo é uma senoide
decaindo cuja altura desliza de ~120 Hz para ~45 Hz. O HPSS o classifica como
**harmônico** e o deixa passar. Na oitava mais grave do CQT, essa varredura
percorre três ou quatro semitons adjacentes.

Em qualquer passagem onde o conteúdo melódico está filtrado — um build-up, um
breakdown — o bumbo vira o mais alto no croma e inventa um acorde cromático que
então se mantém pela seção inteira.

A correção: passa-altas em 110 Hz antes do HPSS, e CQT a partir de **C3**, não
C2. Isso sozinho levou a detecção de tonalidade de **1/4 para 4/4 corretas**.

### Perfis de tonalidade

Vários conjuntos publicados são avaliados e combinados:

- **Krumhansl** (1990) — experimentos de probe-tone, viés clássico.
- **Temperley** (Music Perception 17(1), 1999) — revisão do K-S.
- **Albrecht & Shanahan** (Music Perception 31(1), 2013) — derivado de corpus.
- Um perfil de tríade, para vocabulário de altura pequeno.

### Função harmônica desempata relativo maior/menor

Perfis de classe de altura **não conseguem** separar Lá menor de Dó maior: as
sete notas são as mesmas. Essa é a maior fonte de erro em detecção de
tonalidade, e importa para o DJ — 8B e 5A não são intercambiáveis.

O RETRACK reordena os candidatos por **função de acorde**: cobertura diatônica,
tempo gasto no acorde tônico com a qualidade certa, e posição cadencial.

### Acordes: correlação, não similaridade de cosseno

Templates e quadros de croma são ambos **centrados na média**, tornando isso uma
correlação de Pearson.

Cosseno simples premia qualquer template que sobreponha o componente **plano** do
croma — e quadros borrados (varredura de filtro, drop denso, cauda de reverb)
são majoritariamente componente plano. O template mais denso vence essas
passagens independentemente do que se toca; como esses acordes espúrios tendem a
ser longos, eles dominam a estimativa de tonalidade derivada das durações.

Um prior de complexidade também penaliza acordes estendidos, em unidades de
similaridade de cosseno.

### Decodificação temporal

Viterbi com **custo de mudança explícito**, nas mesmas unidades da evidência.
Expressar isso como probabilidade de auto-transição é a armadilha: 0,92 sobre um
vocabulário de 200 estados implica custo de quase 8 unidades log, que nenhuma
diferença realista de emissão supera — e a faixa inteira colapsa num acorde.

---

## 4. Estrutura

1. Matriz de características **sincronizada por compasso** (croma, MFCC, bandas).
2. Matriz de auto-similaridade e novidade por kernel xadrez —
   **Foote, "Automatic audio segmentation using a measure of audio novelty",
   ICME 2000**.
3. **Prior de frase**: música de dança é construída em potências de dois. Um
   bônus para fronteiras em múltiplos de 4/8/16 compassos elimina quase todos os
   erros de um compasso. É o maior ganho de precisão disponível aqui.
4. Agrupamento aglomerativo para identificar material repetido.
5. Rotulagem funcional por regras inspecionáveis (energia relativa, presença de
   grave, inclinação, posição) — deliberadamente auditável, não caixa-preta.

Comparação: **Kim & Nam, "All-In-One Metrical And Functional Structure Analysis
With Neighborhood Attentions on Demixed Audio", ISMIR 2023** (arXiv:2307.16425).

---

## 5. Separação de camadas

**Demucs / HTDemucs** (Défossez et al., MIT) quando disponível: ~9,0 dB SDR
vocal, o melhor aberto.

Sem torch, um separador espectral embutido: HPSS por filtro de mediana com
`margin=1.0` (mantendo a decomposição **completa** — margem maior descarta
energia que não vai para lado nenhum, apagando justamente o material de médios
ambíguo), roteamento por frequência, e detecção de centro por mid/side.

As máscaras são normalizadas para **particionar** a mistura, e não calculadas
independentemente contra ela — caso contrário as camadas não somam de volta e a
participação de cada uma não significa nada.

### Participação por loudness, não por energia

Soma de quadrados é dominada pelo sub-grave: um bumbo a 50 Hz carrega cem vezes
a energia de um pad a 1 kHz no mesmo nível percebido. Uma divisão por energia
reporta "bateria 72%, todo o resto 0,3%" para uma mistura onde o pad é
claramente audível. A participação é calculada por **loudness com ponderação K**.

---

## 6. Bateria

### Protótipos medidos, não escritos à mão

Cada classe é descrita por um vetor de características físicas (distribuição
espectral, taxa de decaimento, ruidosidade, ataque). Esses vetores são
**medidos** por `tools/calibrate_drum_prototypes.py`, que sintetiza one-shots de
referência e os passa pelo extrator real.

Escrever os valores à mão colocou o centroide espectral do bumbo em 0,13 quando
o valor verdadeiro é **0,69** — e todo bumbo de uma faixa four-on-the-floor foi
classificado como tom.

### Detecção por banda, não full-band

Um detector de onsets full-band **não consegue representar** um bumbo e um
chimbal atingidos no mesmo instante — e nesse repertório isso não é caso raro, é
o que acontece em todo tempo forte. Um onset recebe um rótulo, então ou o bumbo
ou o chimbal se perde, e o sobrevivente arrasta o espectro do outro.

Detecção separada por banda permite eventos simultâneos e restringe o
classificador: nada encontrado apenas acima de 4 kHz pode ser bumbo.

### Resolução de coincidência e gate espectral

Um bumbo tem energia real até 1 kHz, disparando os detectores grave *e* médio.
A resolução mantém a detecção de "corpo" mais forte mais, independentemente, a
de "prato" — refletindo como um kit é realmente tocado.

Um gate sobre o espectro **full-band** rejeita harmônicos de baixo que disparam
o detector médio e parecem toms depois de filtrados.

### Fallback é um limiar, não um competidor

`perc` deliberadamente **não** é um protótipo. Um protótipo catch-all com pesos
baixos tem distância pequena para tudo e engole o kit inteiro.

---

## 7. Mixagem e masterização

### Loudness

Implementação própria de **ITU-R BS.1770-4** com portas em duas etapas, e
**EBU Tech 3341/3342** para faixa de loudness. Os coeficientes de ponderação K
são derivados analiticamente dos protótipos analógicos, não fixados a 48 kHz —
fixá-los mede errado a 44,1 kHz.

Conformidade verificada: senoide de 1 kHz a −23 dBFS estéreo lê **−22,991 LUFS**
(esperado −23,0); canal único lê **−26,001** (esperado −26,0).

Loudness integrado, LRA e pico real juntos identificam a **intenção de
masterização**: −6 LUFS com 3 LU de faixa é master de clube; o mesmo material a
−12 LUFS com 9 LU não é.

### Forense de codec

MP3 e AAC descartam tudo acima de um corte dependente da taxa. Uma queda abrupta
e sustentada em 15–16 kHz é assinatura de 128 kbps. Isso importa: diz se você
está analisando o master ou uma cópia comprimida, e limita o quanto se pode
confiar nos agudos.

### Sidechain

Envelope do alvo promediado sobre uma janela após cada bumbo. A profundidade e o
tempo de release recuperados são exatamente os parâmetros que um aprendiz
precisa — pumping é a técnica definidora da música de dança moderna.

### Reverb

Integração retroativa de Schroeder sobre decaimentos isolados, promediada.

---

## 8. Design sonoro

O mais valioso e o mais especulativo. Estimativa de ADSR, série harmônica,
comportamento do filtro e caráter de unison/detune, produzindo uma receita.

**A confiança é limitada a 65% por construção.** Muitos patches diferentes
produzem espectros indistinguíveis; são hipóteses que reproduzem o que se ouve,
não configurações recuperadas. A interface e os relatórios apresentam assim.

---

## 9. Autoria e originalidade

### Impressão digital

Abordagem clássica de constelação — **Wang, "An industrial-strength audio search
algorithm", ISMIR 2003**. Picos locais espectrais emparelhados em zonas-alvo;
cada par vira um hash de `(f1, f2, Δt)`.

**O histograma de deslocamentos é o ponto crucial.** Hashes compartilhados por si
não significam nada: duas faixas de techno compartilham milhares. O que
identifica cópia real é que um grande número deles **concorda no mesmo
deslocamento temporal**.

Offsets sobrepostos são suprimidos: música em loop se alinha consigo a cada
múltiplo do loop, então uma seção copiada produz uma família inteira de picos
secundários.

### Similaridade musical

Impressão digital responde "é a mesma gravação?". A pergunta interessante é "é a
mesma música?" — uma melodia regravada, uma progressão levantada. Nada disso
compartilha um único pico espectral.

N-gramas de **intervalos** (invariantes a transposição) para melodia; sequências
de acordes relativas à tonalidade para harmonia; sobreposição de padrão para
ritmo; cosseno de embedding para timbre.

### As dimensões permanecem separadas

Disputas de direitos autorais giram esmagadoramente em torno de **melodia**.
Progressões harmônicas praticamente nunca são protegíveis isoladamente. Padrões
de bateria e timbre quase nunca. Os pesos refletem isso, e o relatório imprime o
raciocínio para que se possa discordar.

Contexto: **"Fine-Grained Music Plagiarism Detection", arXiv:2107.09889**.

### Sempre relativo

O resultado é sempre *"quanto desta faixa é explicado por material na sua
biblioteca de referência"*, nunca *"quão original isto é em absoluto"*. Nenhum
programa offline pode comparar com toda a música gravada, e qualquer um que
afirme isso está consultando uma API paga.

---

## 10. Escolha de modelos por hardware

O seletor orça contra VRAM **utilizável** (total menos reserva de desktop) e cai
por quantizações antes de cair para CPU. A escolha errada aqui é um out-of-memory
no meio de um set, então o programa promete menos do que pode.

---

## Referências

- Böck, S. & Widmer, G. (2013). Maximum filter vibrato suppression for onset detection. *DAFx-13*.
- Böck, S. et al. (2016). madmom: a new Python audio and music signal processing library. *ACM MM*. arXiv:1605.07008
- Ellis, D. P. W. (2007). Beat tracking by dynamic programming. *J. New Music Research*, 36(1).
- Foote, J. (2000). Automatic audio segmentation using a measure of audio novelty. *ICME*.
- Krumhansl, C. (1990). *Cognitive Foundations of Musical Pitch*. Oxford.
- Temperley, D. (1999). What's key for key? The Krumhansl-Schmuckler algorithm reconsidered. *Music Perception*, 17(1).
- Albrecht, J. & Shanahan, D. (2013). The use of large corpora to train a new type of key-finding algorithm. *Music Perception*, 31(1).
- Harte, C. et al. (2005). Symbolic representation of musical chords. *ISMIR*.
- Kim, T. & Nam, J. (2023). All-in-one metrical and functional structure analysis with neighborhood attentions on demixed audio. *ISMIR*. arXiv:2307.16425
- Défossez, A. et al. Hybrid Transformers for Music Source Separation (Demucs).
- Bittner, R. et al. (2022). A lightweight instrument-agnostic model for polyphonic note transcription (Basic Pitch). *ICASSP*.
- Radford, A. et al. (2022). Robust speech recognition via large-scale weak supervision (Whisper).
- Wang, A. (2003). An industrial-strength audio search algorithm. *ISMIR*.
- ITU-R BS.1770-4 (2015). Algorithms to measure audio programme loudness and true-peak audio level.
- EBU Tech 3341 / 3342. Loudness metering and loudness range.
