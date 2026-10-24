# Política de segurança

## Versões suportadas

| Versão | Suporte |
|---|---|
| 1.0.x | sim |

## Relatando uma vulnerabilidade

**Não abra uma issue pública para vulnerabilidades.** Use o
[relatório privado do GitHub](https://docs.github.com/pt/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
ou contate os mantenedores diretamente.

Inclua: o que acontece, como reproduzir, e o impacto que você enxerga.
Resposta esperada em até 7 dias.

## Superfície de ataque

O RETRACK processa **arquivos que você fornece** e roda **inteiramente offline**.
Isso limita bastante a superfície, mas há pontos que valem atenção:

### Arquivos de áudio

São decodificados por `libsndfile` e por **FFmpeg em subprocesso**. Ambos já
tiveram CVEs de corrupção de memória em parsers. Mantenha-os atualizados.
O FFmpeg roda como processo separado justamente para conter isso.

### Plugins de áudio (VST3 / CLAP / AU)

**Um plugin é código nativo arbitrário rodando com os seus privilégios.**
Instale apenas plugins de fontes confiáveis.

O scan carrega cada candidato num **subprocesso** com timeout — um plugin que
trava ou faz segfault não derruba o RETRACK, e vai para a lista negra. Isso
protege contra plugins *quebrados*, não contra plugins *maliciosos*.

### Plugins nativos em Python

Executam no processo principal com acesso total. Só instale o que você leu.

### Modelos baixados

Arquivos GGUF e checkpoints de PyTorch são dados, mas o formato `pickle` que o
PyTorch usa por padrão **pode executar código ao carregar**. Baixe pesos apenas
de fontes conhecidas (repositórios oficiais no Hugging Face). O RETRACK nunca
baixa nada sem você pedir.

### Banco de referência

SQLite local com caminhos de arquivo e impressões digitais do seu áudio. Nada
sai da máquina. Se você compartilhar o `.sqlite`, estará compartilhando a lista
de caminhos da sua biblioteca.

### Rede

O RETRACK **não faz nenhuma chamada de rede** durante a análise. As exceções,
ambas explícitas:

1. Download de modelo, que você aprova.
2. Consulta AcoustID, desligada por padrão e que exige a sua própria chave.

Não há telemetria, analytics ou verificação de atualização.

## Boas práticas

- Rode num ambiente virtual.
- Mantenha FFmpeg e libsndfile atualizados.
- Não rode o RETRACK como administrador ou root.
- Analise áudio de origem desconhecida com a mesma cautela de qualquer arquivo
  de origem desconhecida.
