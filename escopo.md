# biograph.IA — Escopo do projeto

> Documento de contexto. Serve de base para os planos de implementação e deve ser
> anexado a qualquer prompt de geração de código.
> Última atualização: 23/09/2026.

## 1. O produto

Plataforma web onde uma pessoa organiza e encontra o próprio acervo digital (fotos e
documentos) perguntando ou filtrando, em vez de navegar por pastas.

O acervo pode estar em duas fontes:

- **Google Drive**, conectado pelo usuário. O arquivo continua lá; guardamos só o que
  extraímos dele.
- **Upload** para a plataforma. Guardamos o arquivo original.

A busca funciona sobre três informações combinadas:

1. Metadados do arquivo (data, GPS, câmera, nome, pasta).
2. Texto extraído de dentro dos documentos.
3. Contexto que o usuário adiciona (evento, local, pessoas, tags).

## 2. Cenário escolhido para o MVP

**Cenário B — somente Google Drive.**

Motivos: o acervo já existe (o usuário vê valor em minutos), não há custo de
armazenamento, e a validação é honesta porque o usuário compara com a busca que ele
já usa hoje. O upload entra depois, em cerca de 80 h de trabalho adicional.

A pergunta que o MVP precisa responder: **somos melhores que a busca nativa do Google
Drive?**

Onde o upload aparecer neste documento, trate como fase posterior, não como escopo do
MVP.

## 3. Decisões tomadas

### 3.1 Sem IA generativa na primeira versão

A busca usa apenas índice de texto e metadados. Motivos:

- **Custo:** sem IA, a operação inteira cabe em planos gratuitos. Com IA seriam cerca
  de US$ 20 a 50 por mês, mais US$ 40 a 80 no processamento inicial dos acervos.
- **Privacidade:** a alternativa gratuita de IA exigiria enviar arquivos pessoais dos
  testadores a um provedor que usa esse conteúdo para melhorar os próprios produtos.
- **Validação antes do gasto:** confirmar primeiro se as pessoas querem organizar e
  buscar o próprio acervo.
- **Sem retrabalho:** cada arquivo já gera um campo de texto pesquisável; na fase com
  IA, a legenda gerada entra nesse mesmo campo.

### 3.2 Banco de dados: PostgreSQL

Decidido contra MongoDB. Motivos: busca de texto nativa com dicionário de português
(ignora acento, reduz palavra ao radical, ranqueia), `pgvector` disponível para a fase
com IA sem trocar de banco, e uma única consulta resolvendo texto + filtros +
paginação. Campos variáveis ficam em coluna `JSONB`.

### 3.3 Linguagens e frameworks

- **Front: React + TypeScript com Vite, entregue como PWA.** O app fica todo atrás de
  login, então renderização no servidor e SEO não agregam. Um SPA estático sobe no plano
  gratuito do Cloudflare Pages sem adaptador. O PWA existe pelo ícone na tela inicial e
  pela notificação de "importação concluída", já que a primeira importação demora e o
  usuário sai do app. No iOS, a notificação só funciona se o app for instalado na tela
  inicial; tratar como bônus.
- **API: Fastify + TypeScript.** Mesma linguagem do front, tipos compartilháveis e menos
  cerimônia que o Nest para o tamanho do projeto. Como não impõe estrutura, o time adota
  pastas por domínio desde o início. Migrar para Nest depois, se o time crescer, troca a
  casca e preserva serviços e handlers.
- **Worker: Python.** Escolhido pela fase seguinte, não pelo MVP: parsing de PDF mal
  formado, OCR (P1) e o processamento da fase com IA são mais fortes em Python. Montar o
  segundo serviço agora custa de 10 a 15 h; reescrever o worker depois custaria de 40 a
  60 h.

**Contrato de fronteira entre as duas linguagens (regra obrigatória):** o worker se
comunica com o resto do sistema **apenas pelo banco de dados**. Ele consome a fila, lê e
grava nas tabelas de arquivos, e nada além disso. Sem biblioteca compartilhada, sem
chamada HTTP entre API e worker, sem tipos duplicados. As migrações têm um dono único, a
API em TypeScript; o worker nunca cria nem altera esquema.

### 3.4 Tipos de arquivo aceitos

| Formato | O que fica pesquisável | Fase |
| --- | --- | --- |
| JPG, JPEG | Nome, pasta, data da foto, cidade (via GPS), câmera, contexto | MVP |
| PNG | Nome, pasta, datas do arquivo, contexto | MVP |
| PDF com texto | Texto completo, metadados, contexto | MVP |
| DOCX | Texto completo, contexto | MVP |
| TXT | Texto completo, contexto | MVP |
| Google Docs | Texto exportado via API do Drive, contexto | MVP |
| PDF escaneado | Só nome e contexto (depende de OCR) | P1 |
| DOC (Word antigo) | Só nome e contexto (depende de conversão) | P1 |

Vídeo e áudio ficam fora.

### 3.5 Usuários

Contas individuais (autônomos e testadores convidados), de 10 a 20 no piloto, cada uma
com o próprio acervo. Sem equipes, sem compartilhamento, sem papéis. Acesso por convite.

### 3.6 Limites operacionais

Valores do piloto, guardados em configuração por usuário (nunca fixos no código), para
liberar mais a um testador específico sem novo deploy.

| Limite | Valor | Motivo |
| --- | --- | --- |
| Arquivos indexados por usuário | 2.000 | Espaço no banco; o texto extraído é o que pesa |
| Arquivos por importação | 500 | O usuário vê valor antes de a importação inteira terminar |
| Texto guardado por arquivo | ~200 KB (cerca de 50 páginas) | Um PDF de 800 páginas sozinho consumiria o banco |
| Tamanho do arquivo baixado | 50 MB | Acima disso, indexa apenas nome e metadados |
| Ritmo de processamento | 1 geocodificação por segundo, com folga na cota do Drive | Evita bloqueio dos serviços gratuitos |

Base do cálculo: 500 MB de banco no plano gratuito, média de 5 KB por arquivo (foto 1 a
2 KB, documento com texto 5 a 50 KB). Vinte testadores com 2.000 arquivos ocupam cerca de
200 MB, deixando folga para índices e crescimento. Em conta paga, o teto por usuário sobe
sem mudança de código.

Regras associadas:

- Só conta arquivo em formato suportado; o resto é ignorado e não entra no contador.
- Arquivo apagado no Drive libera vaga na reindexação seguinte.
- Ao atingir o limite, **nunca parar em silêncio**: informar quantos arquivos foram
  indexados de quantos e oferecer priorizar outra pasta ou outro período.
- Quantos testadores batem o teto é informação de produto, e alimenta a decisão de preço.

## 4. Stack

| Camada | Escolha |
| --- | --- |
| Banco, autenticação, storage | Supabase (PostgreSQL) |
| Busca | `tsvector` do Postgres com dicionário `portuguese` |
| Front | React + TypeScript com Vite, como PWA, hospedado em Cloudflare Pages |
| API | Fastify + TypeScript |
| Worker | Python, processo separado, consumindo fila persistida no Postgres |
| Fila | `pg-boss`, no próprio Postgres |
| Arquivos do Drive | Google Drive API (escopo de leitura), em modo de teste |
| GPS → cidade | Geocodificação reversa do OpenStreetMap, com cache |
| Fase 2 (IA) | `pgvector` no mesmo Postgres + API de modelo externo |

Restrições de plano gratuito: 500 MB de banco, 1 GB de storage, projeto pausa após 1
semana sem uso, até 100 usuários no Drive sem auditoria do Google, cerca de 1 consulta
por segundo na geocodificação.

## 5. Arquitetura

```
App web (React/PWA)  ->  API (Fastify/TS)  ->  Postgres (dados + índice de busca)
                                           \->  Fila (pg-boss, no Postgres)
                                                  \->  Worker (Python)  ->  Google Drive API
                                                                       ->  Geocodificação
                                                                       ->  Postgres

O worker só conversa com o resto pelo banco. Não há chamada HTTP entre API e worker.
```

Regra central: **todo arquivo vira um registro com um campo de texto pesquisável**,
formado por nome + pasta + metadados + texto extraído + contexto do usuário. É esse
campo que a busca consulta, e é nele que a legenda da IA entra na fase 2.

### Pipeline por arquivo (worker)

1. Lê os metadados do arquivo pela API do Drive.
2. Baixa apenas documentos, para extrair o texto, e descarta o binário em seguida.
3. Extrai data, GPS e câmera.
4. Converte GPS em cidade e estado (com cache por coordenada arredondada).
5. Extrai o texto: `pypdf` ou `pdfplumber` para PDF, `python-docx` para DOCX, leitura
   direta para TXT, e export da API do Drive para Google Docs. Metadados de imagem com
   `Pillow` ou `exifread`.
6. Monta o campo de texto pesquisável e atualiza o índice.
7. Marca o arquivo como pronto, ou registra o erro com motivo para reprocessamento.

O processamento é assíncrono e por item: um arquivo com falha não derruba o lote, e
cada item pode ser reprocessado.

## 6. Modelo de dados (esboço)

- `users` — conta, e-mail, data de criação.
- `google_connections` — tokens do usuário, escopo, estado (`ativa`, `expirada`,
  `revogada`).
- `folders` — pastas do Drive selecionadas pelo usuário para indexação.
- `files` — dono, `drive_file_id`, nome, caminho, tipo, tamanho, data do arquivo, data
  de captura, cidade, estado, `metadata JSONB`, `extracted_text`, `search_vector`,
  `status`, `last_verified_at`.
- `file_context` — evento, local, pessoas, tags informados pelo usuário (pode ser
  coluna em `files`, se preferir).
- `jobs` — fila: tipo, referência, tentativas, estado, erro.

Índices: GIN sobre `search_vector`; índices comuns sobre dono, data e tipo. Toda
consulta filtra por dono do arquivo.

## 7. Funcionalidades do MVP

| # | Funcionalidade | Prioridade |
| --- | --- | --- |
| 1 | Login com Google e acesso por convite | P0 |
| 2 | Conexão com o Drive: autorização e seleção de pastas | P0 |
| 3 | Pipeline de extração (metadados, texto, cidade) | P0 |
| 4 | Índice e busca de texto em português, com filtros de período, tipo, cidade e pasta | P0 |
| 5 | Edição de contexto em grade, com seleção múltipla | P0 |
| 6 | Navegação do acervo com filtros e miniaturas | P0 |
| 7 | Resultado abre o arquivo no Drive; confirmação de existência antes de exibir | P0 |
| 8 | Desconectar o Drive e excluir a conta, apagando todos os dados extraídos | P0 |
| 9 | Reindexar pastas sob demanda | P1 |
| 10 | OCR local para PDF escaneado | P1 |
| 11 | Texto de DOC antigo, por conversão | P1 |
| 12 | Linha do tempo do acervo | P1 |

## 8. Fora do escopo

IA generativa (legendas, chat, resumos), busca por significado, contas de empresa e
compartilhamento, vídeo e áudio, sincronização em tempo real com o Drive, outros
provedores de armazenamento, app nativo, reconhecimento facial, cadastro aberto e
cobrança.

## 9. Esforço e prazo

Cerca de 400 horas para o MVP completo do cenário B: 2,5 meses com um desenvolvedor em
tempo integral, ou 8 semanas com dois. Antes disso, uma PoC de 30 a 40 horas valida a
tese central.

## 10. Critérios de sucesso do piloto

- **H1 Busca:** o usuário encontra o arquivo certo em até 3 tentativas em 80% das buscas.
- **H2 Contexto:** metade dos testadores preenche contexto na maioria dos lotes sem ser
  lembrada.
- **H3 Valor além do Drive:** 60% dos testadores acham arquivos mais rápido no app do
  que na busca nativa do Drive.
- **H4 Adoção:** 60% usam a plataforma toda semana durante o piloto.

## 11. Riscos

| Risco | Mitigação |
| --- | --- |
| O tester acha que é igual à busca do Drive | Contexto em massa fácil e filtros prontos na primeira tela; medir H3 |
| Testadores não preenchem contexto | Edição em massa, pedida no momento certo |
| Fotos sem dados de captura (PNG, prints) | Contexto manual; datas do arquivo como alternativa |
| Arquivo apagado no Drive continua nos resultados | Confirmar existência antes de exibir; apagar dados extraídos |
| Token do Google expira ou é revogado | Renovação automática e estado "precisa reconectar" |
| Limite da geocodificação | Fila com ritmo controlado e cache |
| Acervo maior que o teto de 2.000 arquivos | Avisar quantos foram indexados e deixar o usuário priorizar pasta ou período |
| LGPD: dados pessoais nos arquivos | Termo de uso, política de privacidade, exclusão completa, nada enviado a terceiros |
| Limite de 100 usuários sem auditoria do Google | Planejar a verificação antes de abrir o cadastro |

## 12. Fase 2 — IA (depois do MVP)

Legenda automática de fotos, chat sobre o acervo e resumo por tema. A legenda entra no
mesmo campo de texto pesquisável, sem refazer a indexação. Busca por significado com
`pgvector` no mesmo Postgres, em duas camadas: palavra-chave em tudo, vetor apenas em
documentos e legendas. Custo estimado: US$ 60 a 100 por mês, mais US$ 40 a 80 de
processamento inicial.

## 13. Decisões em aberto

- [ ] Critério de convite dos testadores
- [ ] Composição do time e dedicação
- [ ] Região de hospedagem dos dados
- [ ] Provedor de IA para a fase 2
