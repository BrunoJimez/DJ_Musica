# Arquitetura · Architecture

## Princípios

1. **Offline e livre.** Nenhuma API paga, nenhum token, nenhuma chamada de rede
   em tempo de análise. Cada modelo é de pesos abertos e roda localmente.
2. **Degradação graciosa.** Todo componente neural tem um caminho clássico de
   DSP. O programa precisa dar uma resposta útil num notebook sem GPU — e dizer
   qual caminho usou.
3. **Confiança honesta.** Toda estimativa carrega um valor de confiança e o nome
   do método. Engenharia reversa é inferência, não recuperação.
4. **Interoperável.** Resultados saem em formatos abertos (MIDI, DAWproject,
   MusicXML, JSON, WAV), não ficam presos.

## Camadas

```
                    ┌───────────────────────────────┐
                    │  ui/  (PySide6)  ·  cli.py    │
                    └───────────────┬───────────────┘
                                    │
      ┌──────────────┬──────────────┼──────────────┬──────────────┐
      │              │              │              │              │
 ┌────▼────┐  ┌──────▼─────┐  ┌─────▼────┐  ┌──────▼────┐  ┌──────▼────┐
 │ reverse │  │ authorship │  │  learn   │  │   live    │  │  reports  │
 │ projeto │  │  plágio    │  │ highway  │  │  decks    │  │ html/pdf  │
 │ export  │  │ originalid.│  │  aulas   │  │  mixer    │  │  gráficos │
 └────┬────┘  └──────┬─────┘  └─────┬────┘  └──────┬────┘  └──────┬────┘
      └──────────────┴──────────────┼──────────────┴──────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │        analysis/              │
                    │  pipeline · ritmo · tonal ·   │
                    │  estrutura · separação ·      │
                    │  bateria · transcrição ·      │
                    │  timbre · mixagem · design ·  │
                    │  letra · partitura            │
                    └───────────────┬───────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
        ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
        │  audio/   │         │  system/  │         │    ai/    │
        │ io · dsp  │         │ hardware  │         │  regras   │
        │ loudness  │         │ deps      │         │  LLM      │
        └───────────┘         │ modelos   │         └───────────┘
                              └───────────┘
```

Dependências apontam **para baixo**. `analysis` nunca importa de `ui`;
`audio` não sabe que `analysis` existe. `plugins/` e `hardware/` conectam-se
lateralmente onde necessário.

## Ordem do pipeline

A ordem é ditada pelas dependências reais:

```
carregar
   └─► ritmo ──────────────────────────► (a grade é o sistema de coordenadas)
          └─► separação ─┬─► tonal (usa a camada de baixo p/ desambiguar tônica)
                         ├─► bateria (precisa da camada de bateria limpa)
                         ├─► transcrição (uma camada por vez)
                         ├─► design sonoro (precisa das notas)
                         ├─► letra (precisa da camada vocal)
                         └─► mixagem (precisa das camadas p/ sidechain)
   └─► estrutura (usa os downbeats)
   └─► timbre
```

Cada estágio roda dentro de `_run_stage`, que o cronometra e **contém as suas
falhas**: uma faixa cuja transcrição de letra quebra ainda entrega andamento,
tonalidade e arranjo.

## Contrato de dados

`analysis/features.py` define tudo. Duas regras valem em todo o módulo:

- **Toda estimativa carrega confiança e método.** Um BPM de 128,0 vindo de um
  bumbo limpo e um adivinhado de um piano rubato não são a mesma afirmação.
- **Tudo é serializável em JSON.** É o que faz o cache, os relatórios e os
  exportadores compartilharem um único caminho de código.

## Cache

Chaveado por **conteúdo do arquivo** (blake2b sobre blocos estratificados mais
o tamanho), não pelo caminho. Renomear um arquivo não invalida o cache; editá-lo
invalida. Arrays intermediários pesados (croma, envelope, SSM) **não** são
cacheados — são recomputados sob demanda, mantendo uma entrada em algumas
centenas de kB em vez de dezenas de MB.

`CACHE_SCHEMA_VERSION` em `version.py` invalida tudo quando o formato muda.

## Tempo real

`live/` roda dentro do callback de áudio. As restrições:

- **Nenhuma alocação no caminho de renderização.** Buffers pré-alocados. Uma
  pausa do coletor de lixo no meio de um set é um dropout na pista.
- **Mudanças de parâmetro são rampadas.** Um ganho que salta entre blocos
  estala audivelmente.
- **Nenhuma exceção escapa.** Uma exceção no callback mata o stream.
- **Ler além do fim retorna silêncio**, não levanta erro.

`audio/dsp.py` é NumPy/SciPy puro, sem librosa, justamente para poder ser usado
ali — os imports preguiçosos e o JIT do numba seriam inaceitáveis.

## Threading

| Onde | Modelo |
|---|---|
| Análise | `QThread` (GUI) ou síncrona (CLI) |
| Áudio | callback do PortAudio, prioridade alta |
| MIDI | thread própria, fila para a UI |
| Scan de plugins | **subprocesso por plugin** |
| Relatórios | `QThread` |

O scan de plugins usa subprocessos porque um VST mal escrito trava, faz segfault
ou abre um diálogo modal ao carregar. No processo principal, qualquer um desses
derruba o programa. Um subprocesso morto custa um plugin e uma entrada na lista
negra.

## Pontos de extensão

| Quero… | Onde |
|---|---|
| Adicionar uma medição | novo módulo em `analysis/`, chamar de `pipeline.py` |
| Adicionar um formato de export | `reverse/exporters/`, registrar em `EXPORTERS` |
| Adicionar conhecimento ao conselheiro | uma função com `@rule` em `ai/rules.py` |
| Suportar uma controladora | entrada em `hardware/controllers.py` + JSON de mapeamento |
| Estender sem tocar no código | `RetrackPlugin` — veja [PLUGINS.md](PLUGINS.md) |

## Testes

`tests/` valida contra o **gerador de faixa sintética** em
`examples/generate_demo_track.py`, que produz áudio com verdade conhecida —
BPM exato, tonalidade exata, progressão exata, fronteiras de seção exatas.

Isso resolve dois problemas de uma vez: não há material protegido no repositório,
e as asserções são contra verdade real em vez de contra o que se acredita que a
verdade seja.
