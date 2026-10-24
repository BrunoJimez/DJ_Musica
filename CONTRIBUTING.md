# Contribuindo · Contributing

Obrigado pelo interesse. Este documento cobre o essencial.

---

## Preparando o ambiente

```bash
git clone https://github.com/BrunoJimez/retrack-studio.git && cd retrack-studio
```

```bash
python3.11 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -e ".[gui,live,reports,dev]"
```

```bash
pytest tests/ -v
```

Os testes rodam contra a faixa sintética gerada por
`examples/generate_demo_track.py`. **Nunca adicione áudio protegido ao
repositório** — se precisar de um caso de teste novo, adicione um preset ao
gerador.

---

## O que faz um bom pull request aqui

### Corrija a causa, não o sintoma

Este código tem um histórico de bugs que pareciam ajustes de parâmetro e eram
defeitos reais. Alguns exemplos, todos documentados no código:

- O BPM saía 1,2 unidade errado. A tentação era ajustar um limiar; a causa era
  usar a mediana dos intervalos como período.
- A tonalidade saía relativa maior. A causa era o bumbo poluindo a oitava grave
  do croma, porque o HPSS classifica um bumbo como harmônico.
- O classificador de bateria rotulava tudo igual. A causa era um protótipo
  catch-all com pesos baixos servindo de atrator universal.

Se um teste falha, encontre **por quê** antes de mexer num número.

### Números vêm de medição

Se você adicionar constantes — protótipos, limiares, pesos — diga de onde
vieram. Escrever protótipos de bateria à mão colocou o centroide do bumbo em
0,13 quando o valor real é 0,69. Existe uma ferramenta para isso:

```bash
python tools/calibrate_drum_prototypes.py --weights
```

### Comentários explicam o porquê

O código já diz *o que* faz. Um comentário útil explica a decisão não óbvia, a
armadilha evitada, ou por que a abordagem ingênua não funciona. Comentários que
reafirmam a linha seguinte serão pedidos para remoção.

### Degradação graciosa não é opcional

Toda dependência nova é **opcional** até prova em contrário. Registre-a em
`system/deps.py` com:

- o que ela habilita;
- o que o programa faz sem ela;
- como instalá-la;
- **a licença**.

Se não houver plano B possível, diga isso explicitamente — foi o que fizemos
com a transcrição de letra, que não tem alternativa clássica.

### Nenhuma API paga

Regra do projeto, sem exceções. Nenhum token, nenhuma cobrança por uso, nenhum
serviço de nuvem obrigatório. Modelos precisam ser de pesos abertos e rodar
localmente.

---

## Estilo

```bash
ruff check src tests && ruff format src tests
```

- Linha de 100 colunas.
- Type hints em APIs públicas.
- Docstrings explicando o *propósito*, não repetindo a assinatura.
- Português ou inglês nos comentários — o código existente usa inglês; mantenha
  a consistência dentro de cada arquivo.

---

## Testes

Todo comportamento novo precisa de teste. Todo bug corrigido precisa de um teste
de regressão que **falharia antes** da correção — vários testes existentes têm
uma docstring dizendo exatamente qual bug eles guardam.

Marcadores disponíveis:

```python
@pytest.mark.slow          # mais de alguns segundos
@pytest.mark.needs_torch   # exige a pilha torch/demucs
@pytest.mark.needs_gui     # exige PySide6 e um display
```

```bash
pytest tests/ -m "not slow"
```

---

## Onde mexer

| Quero… | Vá para |
|---|---|
| Melhorar uma medição | `src/retrack/analysis/` |
| Adicionar um formato de export | `src/retrack/reverse/exporters/` |
| Ensinar algo ao conselheiro | `src/retrack/ai/rules.py` (uma função com `@rule`) |
| Suportar uma controladora | `src/retrack/hardware/controllers.py` |
| Mexer na interface | `src/retrack/ui/` |
| Estender sem tocar no núcleo | escreva um plugin — [docs/PLUGINS.md](docs/PLUGINS.md) |

Antes de mudar arquitetura, leia [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Antes de mexer em algoritmos, leia
[docs/SCIENTIFIC_BASIS.md](docs/SCIENTIFIC_BASIS.md) — a decisão que você quer
reverter pode estar documentada com o motivo.

---

## Relatando bugs

Inclua a saída de:

```bash
retrack doctor
```

E, para problemas de análise, **como reproduzir com a faixa demo**:

```bash
retrack demo --preset techhouse
```

Se o problema só acontece com o seu áudio, descreva o material (gênero, BPM,
se é lossy) — não envie o arquivo.

---

## Licença das contribuições

Ao enviar um PR você concorda em licenciar sua contribuição sob a **MIT**, a
mesma do projeto. Se você adicionar uma dependência com licença diferente,
registre-a em [NOTICE.md](NOTICE.md) e explique as implicações.
