# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [1.0.0] — 2026-08-01

Primeira versão. Programa completo de engenharia reversa, aprendizado e
performance ao vivo, rodando inteiramente offline.

### Análise

- Rastreamento de ritmo com detecção multibanda de onsets, tempograma com
  filtro pente e programação dinâmica (Ellis 2007). Ajuste linear da grade
  leva o erro de BPM a **< 0,005** em material quantizado.
- Correção explícita de oitava de andamento — drum & bass a 174 BPM não é mais
  reportado como 87.
- Refino sub-frame na forma de onda, removendo o viés sistemático de ~10 ms que
  a STFT centrada introduz.
- Swing medido por densidade kernel na banda de chimbais, com "reto" como
  hipótese nula.
- Tonalidade por múltiplos perfis publicados (Krumhansl, Temperley,
  Albrecht-Shanahan) reordenados por função harmônica, resolvendo a confusão
  com a tônica relativa.
- Reconhecimento de acordes por correlação de Pearson com prior de complexidade
  e decodificação Viterbi com custo de mudança explícito.
- Segmentação estrutural com novidade de Foote e prior de frase em potências de
  dois.
- Separação de camadas: Demucs quando disponível, separador espectral embutido
  caso contrário. Participação calculada por loudness, não por energia.
- Transcrição de bateria por detecção em bandas separadas, com protótipos
  **medidos** e gate espectral full-band.
- Transcrição melódica: Basic Pitch ou rastreador CQT embutido.
- Medição de loudness ITU-R BS.1770-4 / EBU R128 própria, conforme dentro de
  0,01 LU no sinal de teste.
- Detecção de sidechain, reverb, delay, saturação e forense de codec.
- Reconstrução de design sonoro com confiança limitada a 65% por construção.
- Transcrição de letra via faster-whisper, com filtro de alucinações.

### Engenharia reversa

- Modelo de projeto editável em compassos: faixas, clipes, notas, automação,
  dispositivos, marcadores.
- Detecção de loop, reduzindo repetições a um ciclo.
- Nove exportadores: MIDI, DAWproject, Reaper, Ableton, JSON, receita,
  rekordbox, Serato, Mixxx.
- Receita de construção passo a passo, ordenada como um produtor trabalha.

### Aprendizado

- Autoestrada de notas estilo Guitar Hero, com janelas de tempo que escalam com
  a velocidade de reprodução.
- Plano de aulas com travas de progressão, rampa de andamento e exercícios de
  remediação focados na faixa mais fraca.
- Correção específica: detecta viés de antecipação/atraso e diz o que fazer.

### Ao vivo

- Motor de 2 a 4 decks com pitch, keylock, loops, hot cues automáticos.
- Mixer com EQ de 3 bandas, filtro varrido, crossfader com três curvas.
- Limitador de master com ataque rápido e clip de segurança.
- Sincronismo de andamento e fase, gravação de set, modo pânico.
- Planejador de setlist por compatibilidade Camelot e curva de energia.

### Autoria

- Impressão digital de constelação própria, offline.
- Similaridade melódica (invariante a transposição), harmônica, rítmica,
  tímbrica e estrutural, reportadas separadamente com o peso jurídico de cada
  uma.
- Biblioteca de referência em SQLite com índice invertido.
- Diagnóstico estatístico de originalidade, sempre com o escopo declarado.

### Relatórios

- HTML autocontido com todos os gráficos embutidos, PDF, Markdown, JSON.
- Partitura MusicXML, cifra, tablatura de bateria, lead sheet.
- Português e inglês.

### Sistema

- Perfil de hardware, matriz de capacidades e seleção de modelos por VRAM
  utilizável.
- Host VST3/CLAP/AU via pedalboard, com scan em subprocesso.
- API de plugins nativos em Python.
- Banco de controladoras MIDI, mapeamento genérico e MIDI learn.
- Relatório de compatibilidade de hardware de DJ.

### Interface

- Console gráfico com 10 abas, três temas e modo palco.
