# Prompts para gerar os planos de implementação

Cada prompt abaixo gera o **plano** de uma etapa, não o código. Rode um por vez, na
ordem, e revise o plano antes de partir para a implementação.

## Como usar

1. Anexe o `escopo.md` na conversa.
2. Cole o prompt da etapa.
3. Revise o plano, corrija o que estiver errado e só então peça o código.
4. Ao gerar o plano da etapa seguinte, informe o que já existe no repositório.

Regras que valem para todos os prompts:

- Perguntar antes de assumir qualquer coisa que o escopo não define.
- Nada de IA, embeddings ou busca vetorial no MVP.
- Nada de upload de arquivos: o acervo vem só do Google Drive.
- Toda consulta ao banco filtra pelo dono do arquivo.
- O worker (Python) se comunica com o resto apenas pelo banco: sem chamada HTTP entre API
  e worker, sem biblioteca compartilhada, sem tipos duplicados. As migrações têm um dono
  único, a API em TypeScript.

## As três fases

| Bloco | Etapas | Esforço | O que é |
| --- | --- | --- | --- |
| **Fase 0 — PoC** | 0 | 30 a 40 h | Prova a tese. Código descartável, exceto a extração |
| **Fase 1 — MVP** | 1 a 8 | ~400 h | O produto que vai ao piloto |
| **Fase 2 — IA** | 9 | a estimar | Só depois de o piloto validar as hipóteses |

Entre a fase 0 e a fase 1 existe um portão de decisão. Não comece a etapa 1 antes de
passar por ele.

---

## Prompt base (colar no início de cada etapa)

```
Você é um engenheiro sênior planejando a implementação do projeto descrito no escopo em
anexo. Estamos no cenário B (somente Google Drive), sem IA, com PostgreSQL. A stack está
definida: front em React + TypeScript (Vite, PWA), API em Fastify + TypeScript, worker em
Python, fila com pg-boss no próprio Postgres, tudo sobre Supabase.

Sua tarefa é produzir um PLANO DE IMPLEMENTAÇÃO da etapa indicada abaixo. Não escreva
código de produção; no máximo assinaturas de função, esquema de tabela e contratos de
API.

O plano deve conter:
1. Objetivo da etapa em uma frase.
2. Pré-requisitos (o que precisa estar pronto antes).
3. Decisões técnicas a tomar, cada uma com as opções e a sua recomendação justificada.
4. Tarefas em ordem de execução, com estimativa em horas por tarefa.
5. Contratos: tabelas, endpoints, formato dos dados.
6. Casos de erro e como tratá-los.
7. Critérios de aceite verificáveis.
8. O que fica explicitamente fora desta etapa.

Regras:
- Se faltar informação para decidir algo, pergunte antes de assumir.
- Prefira a solução mais simples que atenda ao critério de aceite.
- Considere os limites dos planos gratuitos descritos no escopo.
- Aponte onde a decisão desta etapa afeta a fase 2 (IA).

ETAPA: <cole aqui a etapa desejada>
```

---

# Fase 0 — PoC (código descartável)

## Etapa 0 — PoC: provar a tese

```
ETAPA 0 — PoC de 30 a 40 horas.

Objetivo: provar que, lendo uma pasta do Google Drive e indexando metadados e texto,
encontramos arquivos melhor do que a busca nativa do Drive.

Escopo: uma única conta (a do desenvolvedor), rodando localmente, sem deploy, sem
cadastro, sem contexto do usuário, sem tratamento de erro elaborado. Uma tela de busca
com filtros de ano e tipo.

Na PoC, monte a extração como script Python isolado, que é a linguagem definida para o
worker no produto. O resto pode ser o mais simples possível, inclusive sem API separada.

Inclua no plano:
- O passo a passo da configuração no Google Cloud, incluindo tela de consentimento,
  escopos necessários e como adicionar testadores.
- Um protocolo de avaliação: 10 buscas reais de uma pessoa com Drive cheio, comparando
  app e busca nativa do Drive, medindo se achou, em quanto tempo e em que posição.
- O critério de corte: abaixo de quantos acertos a tese não se sustenta.
```

---

## Portão de decisão: a PoC passou?

Avalie com as 10 buscas reais definidas na etapa 0, feitas por alguém que não seja você.

| Resultado | Decisão |
| --- | --- |
| Ganhamos do Drive em 6 ou mais das 10 buscas | Seguir para a etapa 1 |
| Ganhamos em 4 ou 5 | Investigar o que falhou (extração? ranqueamento? tipo de arquivo?) e repetir o teste antes de seguir |
| Ganhamos em 3 ou menos | Parar. O problema é de tese, não de execução. Reavaliar o cenário escolhido |

O que fazer com o código da PoC:

- **Aproveitar:** o script Python de extração (leitura do Drive, metadados, texto). Ele é
  a base do worker da etapa 3.
- **Descartar:** a tela de busca. Foi feita sem autenticação, sem multiusuário e sem
  tratamento de erro; reaproveitar sai mais caro que refazer.
- **Guardar:** o conjunto de 10 buscas com o resultado esperado. Vira o teste de
  qualidade da busca na etapa 4.

---

# Fase 1 — MVP (etapas 1 a 8)

## Etapa 1 — Fundação

```
ETAPA 1 — Fundação do projeto.

Escopo: estrutura do repositório, configuração de ambientes, Supabase provisionado,
migrações de banco, login com Google, acesso por convite, deploy do front (React/Vite no
Cloudflare Pages) e da API (Fastify), esqueleto do worker em Python, health check e log
básico.

Inclua no plano:
- Organização do repositório com três serviços em duas linguagens (monorepo ou repos
  separados), com recomendação justificada.
- Estrutura de pastas por domínio na API, já que o Fastify não impõe estrutura.
- Estratégia de migração de banco e como o worker em Python acompanha mudanças de esquema
  sem poder alterá-lo.
- Como os segredos são guardados em cada um dos três serviços.
- Como um convite é criado e consumido.
- Configuração mínima do PWA (manifest, ícone, service worker) e o que fica para depois.
```

## Etapa 2 — Conexão com o Google Drive

```
ETAPA 2 — Conexão com o Google Drive.

Escopo: autorização OAuth separada do login, guarda e renovação de tokens, seleção das
pastas a indexar, listagem dos arquivos dessas pastas e criação dos itens na fila.

Inclua no plano:
- Quais escopos pedir e por quê, e o impacto na verificação do Google.
- Como a tela explica ao usuário, antes da autorização, o que será lido e o que será
  guardado.
- Renovação de token, e o que acontece quando o usuário revoga o acesso.
- Paginação da listagem de arquivos e como lidar com pastas grandes.
- Como o usuário acompanha o progresso da importação.
```

## Etapa 3 — Worker de extração

```
ETAPA 3 — Worker de extração.

Escopo: worker em Python consumindo a fila persistida no Postgres, processando um
arquivo por vez, extração
de metadados (data, GPS, câmera), download apenas de documentos, extração de texto de
PDF, DOCX, TXT e Google Docs, conversão de GPS em cidade com cache, montagem do campo
de texto pesquisável e atualização do status do arquivo.

Inclua no plano:
- Desenho da fila: estados, tentativas, backoff, como evitar processamento duplicado.
- Bibliotecas Python candidatas para cada formato (PDF, DOCX, TXT, EXIF), com prós e
  contras, considerando PDFs mal formados.
- Como o worker consome a fila do pg-boss a partir do Python, respeitando o contrato de
  se comunicar apenas pelo banco.
- Empacotamento e execução do serviço Python: dependências, ambiente e imagem.
- Limite de ritmo da geocodificação e estratégia de cache.
- O que fazer com PDF sem texto e com arquivo corrompido.
- Como o worker roda no piloto (máquina do dev) e o que muda ao hospedá-lo.
- Como a legenda gerada por IA entrará nesse mesmo fluxo na fase 2.
```

## Etapa 4 — Índice e busca

```
ETAPA 4 — Índice e busca.

Escopo: busca de texto em PostgreSQL com dicionário de português, combinada com filtros
de período, tipo, cidade e pasta, com ranqueamento e paginação.

Inclua no plano:
- Como montar e manter o tsvector, com pesos por origem do texto (nome, contexto do
  usuário, texto do documento).
- Índices necessários e impacto no tamanho do banco.
- Ranqueamento: o que deve pesar mais e por quê.
- Reconhecimento de períodos escritos, como "março de 2024".
- Como medir a qualidade da busca (conjunto de consultas de teste com resultado
  esperado).
- Onde o pgvector se encaixaria na fase 2, sem refazer este índice.
```

## Etapa 5 — Contexto do usuário

```
ETAPA 5 — Contexto do usuário.

Escopo: grade de miniaturas com seleção múltipla, edição em massa de evento, local,
pessoas e tags, e reindexação dos arquivos alterados.

Inclua no plano:
- Modelo de dados do contexto e das tags.
- Fluxo de edição em massa e o que acontece com centenas de arquivos selecionados.
- Como as miniaturas são obtidas sem guardar o arquivo.
- Como o produto incentiva o preenchimento sem ser chato (meta H2 do escopo).
```

## Etapa 6 — Navegação e resultados

```
ETAPA 6 — Navegação e resultados.

Escopo: tela principal do acervo com filtros prontos (ano, cidade, tipo, pasta), grade
de resultados, abertura do arquivo no Drive e confirmação de existência antes de
exibir.

Inclua no plano:
- Como a primeira tela após a importação demonstra valor em segundos (meta H3).
- Estratégia de verificação de existência sem estourar a cota da API.
- O que exibir quando o arquivo foi apagado ou perdeu permissão.
- Estados vazios, carregando e erro.
```

## Etapa 7 — Privacidade e conformidade

```
ETAPA 7 — Privacidade e conformidade.

Escopo: desconectar o Drive, excluir a conta com remoção de todos os dados extraídos,
termo de uso, política de privacidade e registro de consentimento.

Inclua no plano:
- O que exatamente é apagado, em que ordem, e o que fazer com dados já em cache.
- Requisitos da LGPD aplicáveis a este produto, em linguagem prática.
- Exigências do Google para apps que leem o Drive, e o que precisa estar pronto antes
  de passar de 100 usuários.
```

## Etapa 8 — Piloto

```
ETAPA 8 — Preparação do piloto.

Escopo: instrumentação para medir H1 a H4, tela de erro amigável, monitoramento básico,
roteiro de onboarding dos testadores e canal de feedback.

Inclua no plano:
- Que eventos registrar para medir cada hipótese, sem coletar dado pessoal
  desnecessário.
- Como comparar o tempo de busca no app e no Drive de forma justa.
- Roteiro da primeira sessão com um testador.
- Critérios que indicam parar, ajustar ou seguir para a fase 2.
```

---

# Fase 2 — IA (só depois do piloto)

## Etapa 9 — Camada de IA

```
ETAPA 9 — Fase 2, camada de IA.

Escopo: legenda automática de fotos, busca por significado com pgvector e, na sequência,
chat e resumo por tema sobre o acervo.

Inclua no plano:
- Onde a legenda entra no fluxo já existente, sem refazer a indexação, aproveitando que
  o worker já está em Python.
- Estratégia de duas camadas: palavra-chave em tudo, vetor só em documentos e legendas.
- Dimensão dos vetores e impacto no tamanho do banco, considerando os limites do plano.
- Processamento em lote para reduzir custo, e estimativa por mil arquivos.
- Consentimento necessário para enviar conteúdo do usuário a um provedor externo.
- Como a resposta do chat cita os arquivos de origem e o que fazer quando não há base.
```

---

## Prompt de revisão (rodar depois de cada plano)

```
Revise criticamente o plano acima como se fosse outro engenheiro sênior. Aponte:
- premissas não declaradas;
- tarefas subestimadas, com nova estimativa;
- casos de erro esquecidos;
- qualquer coisa que contraria o escopo anexo;
- o que dá para cortar sem comprometer o critério de aceite.
Seja específico e não elogie o plano.
```
