# Plugins

Duas coisas diferentes vivem sob a mesma palavra.

---

## 1. Seus plugins de áudio (VST3 / CLAP / AU)

O RETRACK hospeda plugins externos através do
[pedalboard](https://github.com/spotify/pedalboard) da Spotify.

```bash
pip install -e ".[plugins]"
```

```bash
retrack plugins scan
```

```bash
retrack plugins list
```

Ou use a aba **Plugins** na interface.

### Aviso de licença

O `pedalboard` é **GPL-3.0**, e leva junto o JUCE e o SDK do VST3. Usar na sua
máquina não muda nada. **Redistribuir** um pacote que o inclua — um `.exe` do
PyInstaller, uma imagem Docker, um instalador — torna esse pacote GPL, e você
precisa oferecer o código-fonte correspondente completo.

É por isso que a hospedagem de plugins é um extra opcional carregado por um
adaptador fino (`retrack/plugins/host.py`), e não uma dependência do núcleo.

Prefira **CLAP** quando puder: é um padrão aberto com licença MIT.

### Por que o scan usa subprocessos

Um VST mal escrito trava, faz segfault ou abre um diálogo modal ao carregar. No
processo principal, qualquer um desses derruba o RETRACK. Cada candidato é
carregado num interpretador separado; um subprocesso morto custa um plugin e uma
entrada na lista negra.

O resultado fica em cache num SQLite, chaveado por caminho, data de modificação
e tamanho — um novo scan só toca no que mudou.

### Onde ele procura

| SO | Pastas |
|---|---|
| Windows | `Program Files\Common Files\VST3`, `...\CLAP`, `VSTPlugins`, e as equivalentes por usuário |
| macOS | `/Library/Audio/Plug-Ins/{VST3,Components,CLAP}` e `~/Library/...` |
| Linux | `/usr/lib/vst3`, `/usr/local/lib/clap`, `~/.vst3`, `~/.clap` |

Adicione outras pelo botão **Add folder…** ou em `settings.toml`.

---

## 2. Plugins nativos do RETRACK (Python)

Estes fazem coisas que um VST não pode: adicionar um estágio de análise, um
formato de exportação, ou uma regra ao conselheiro.

Coloque um `.py` na pasta de plugins (o `retrack doctor` mostra o caminho):

```python
from retrack.plugins import RetrackPlugin


class AfinadorDeBumbo(RetrackPlugin):
    name = "Afinador de bumbo"
    version = "1.0"
    author = "você"
    description = "Reporta a fundamental do bumbo e sugere a tonalidade."
    category = "advisor"

    def provide_insights(self, analysis):
        from retrack.ai.rules import Insight

        if not analysis.drums:
            return []

        kicks = analysis.drums.hits_of("kick")
        if len(kicks) < 8:
            return []

        return [
            Insight(
                category="mix",
                title="Afinação do bumbo",
                observation=f"{len(kicks)} bumbos detectados.",
                why=(
                    "Um bumbo afinado na tônica da faixa soma com o baixo em vez "
                    "de brigar com ele."
                ),
                action=f"Tente afinar o bumbo para {analysis.key_name.split()[0]}.",
                confidence=0.5,
            )
        ]
```

### Ganchos disponíveis

| Método | Quando é chamado |
|---|---|
| `setup(context)` | Uma vez, ao carregar |
| `teardown()` | Ao descarregar ou encerrar |
| `on_analysis_complete(analysis)` | Depois que uma análise termina |
| `on_project_built(project, analysis)` | Depois que o projeto é reconstruído |
| `provide_insights(analysis)` | Ao rodar o conselheiro |
| `process_audio(audio, sr)` | Processamento offline |
| `export(project, path)` | Formato de exportação próprio |

Todos são opcionais. Sobrescreva só o que você usa.

### Categorias

`analysis` · `effect` · `exporter` · `advisor` · `ui`

A categoria é informativa — aparece na interface e permite filtrar.

### Regras

- Uma falha ao carregar **nunca** derruba o programa: o erro aparece na lista.
- O plugin roda no processo principal. Não bloqueie: trabalho longo vai para
  uma thread.
- Nada de rede sem avisar o usuário. O RETRACK promete ser offline; um plugin
  que quebra essa promessa quebra o produto.
