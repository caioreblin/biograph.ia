# Etapa 0 — PoC: plano de implementação

## Contexto

A pasta `biographai/` hoje tem só `escopo.md` e `prompts-planos.md`, e não é um
repositório git. A Etapa 0 é a PoC de 30 a 40 h que precisa passar pelo portão de
decisão em `prompts-planos.md` antes da Fase 1. O script de extração em Python é
aproveitado depois como base do worker da Etapa 3. A tela de busca é descartada. As 10
buscas viram o teste de qualidade da Etapa 4.

**O que eu faço ao aprovar este plano (nesta sessão):**
1. `git init -b main` em `biographai/`.
2. Crio o `.gitignore` (`.env`, `credentials.json`, `token.json`, `.venv/`,
   `__pycache__/`, `*.pyc`, `.streamlit/secrets.toml`).
3. Salvo este plano como `docs/etapa-0-poc.md`.
4. Faço o commit inicial com `escopo.md`, `prompts-planos.md`, `.gitignore` e
   `docs/etapa-0-poc.md`.

**Modo de execução (pedido por você):**
- Executo **uma tarefa por vez**, na ordem da seção 4, começando pela tarefa 0 (git).
- Ao fim de cada tarefa, paro, mostro o que foi feito e como conferir, e **espero o seu
  aceite** para seguir.
- Nos passos que só você pode fazer, eu dou as instruções e espero você confirmar:
  - tarefa 1: escrever as 10 buscas;
  - tarefa 2: Google Cloud e autorização OAuth no navegador;
  - tarefa 4: criar a conta e o projeto no Supabase, e colar a `DATABASE_URL` no `.env`;
  - tarefa 13: fazer as buscas.
- Posso instalar as ferramentas necessárias, como o Python 3.12 via `winget` e os pacotes
  pip no `.venv`.
- Não subo o Streamlit nem abro o navegador sem você pedir (regra do seu CLAUDE.md
  global). Na tarefa 12, entrego o comando para você rodar ou peço autorização.
- Commits: um por tarefa aceita, e o da tarefa 1 precisa vir antes do código de busca.

**Decisões já confirmadas com você:**
- Quem avalia é o próprio desenvolvedor, no próprio Drive.
- O banco é o Supabase na nuvem, no plano grátis.
- A tela é em Streamlit.
- A indexação lê uma pasta raiz escolhida, de forma recursiva e sem o teto de 2.000
  arquivos.

**Estado da máquina:** tem Node 22 e git 2.51. Não tem Python (só o alias da Microsoft
Store) nem Docker.

---

## 1. Objetivo

Provar, com 10 buscas reais registradas antes de existir o código de busca, que um
índice Postgres feito a partir de metadados e texto de uma pasta do Drive encontra o
arquivo certo mais vezes e mais rápido do que a busca nativa do Drive.

## 2. Pré-requisitos

- Conta Google pessoal do desenvolvedor com um Drive cheio, e uma pasta raiz escolhida.
  Recomendo usar o próprio "Meu Drive" se tiver até cerca de 20 mil arquivos
  suportados, porque isso simplifica a comparação justa.
- Python 3.14 (já instalado pelo Python Install Manager, `py -3.14`). Opcional: desativar o alias da
  Store em *Configurações > Aplicativos > Aliases de execução*.
- Conta no Supabase e um projeto no plano grátis, criado na tarefa 3.
- Um cronômetro, ou gravação de tela com `Win+Alt+R` (Xbox Game Bar), para a avaliação.
- As 10 buscas escritas e registradas em commit **antes** da tarefa 10 (veja a
  seção 9).

## 3. Decisões técnicas

| # | Decisão | Opções | Recomendação e motivo |
|---|---|---|---|
| D1 | Banco | Supabase na nuvem / Postgres nativo / Docker com Supabase CLI | **Supabase na nuvem** (confirmado). Não exige instalação, usa a mesma versão e as mesmas extensões do produto e mede de verdade o custo por arquivo. Conectar pelo **Session pooler**, porque a conexão direta do plano grátis é só IPv6. |
| D2 | Tela | Streamlit / React com supabase-js / FastAPI | **Streamlit** (confirmado). Mantém uma linguagem só, a consulta roda no servidor e nenhuma chave vai para o navegador. |
| D3 | Escopo OAuth | `drive.readonly` / `drive.metadata.readonly` / `drive.file` | **`drive.readonly`**. O `metadata.readonly` não baixa nem exporta conteúdo. O `drive.file` só enxerga arquivos criados ou abertos pelo app, então não serve para ler uma pasta. Por ser escopo *restrito*, a Fase 1 vai exigir verificação e avaliação de segurança (CASA) antes de passar de 100 usuários. |
| D4 | Tipo de cliente OAuth | App para computador / App da Web | **App para computador (Desktop)**. O fluxo `InstalledAppFlow.run_local_server()` usa redirect de loopback e não exige configurar URI. |
| D5 | EXIF das fotos | Baixar e ler com Pillow ou exifread / usar `imageMediaMetadata` do Drive | **`imageMediaMetadata`**. A API já devolve data de captura, GPS e câmera. Assim não se baixa nenhuma foto, o que segue a regra "baixa apenas documentos" e economiza cota. |
| D6 | Extração de PDF | `pypdf` / `pdfplumber` | **`pypdf`**. É puro Python, mais rápido e basta para PDF com texto. A comparação com PDFs mal formados fica para a Etapa 3. |
| D7 | Data usada no filtro de ano | Data de criação no Drive / data de modificação / data derivada | **`effective_date` derivada**: primeiro a data de captura do EXIF, depois a data interna do documento (metadado do PDF ou DOCX), por último a menor entre criação e modificação no Drive. Grava-se também a origem da data. A data de envio ao Drive costuma estar errada para documentos antigos, e é aqui que dá para ganhar do Drive. |
| D8 | Índice de texto | `unaccent()` em trigger / configuração de busca própria com unaccent | **Configuração própria `pt_unaccent`** (cópia de `portuguese` com `unaccent` antes de `portuguese_stem`) e **coluna gerada** `search_vector`. Com um `regconfig` constante a expressão é imutável, então dispensa trigger. |
| D9 | Semântica da consulta | Só E (AND) / E com recuo para OU / trigramas | **`websearch_to_tsquery` (AND); se não houver resultado, repetir com os termos em OU**. É simples e evita a tela vazia. O `pg_trgm` para erro de digitação fica para a Etapa 4. |
| D10 | Ranqueamento | `ts_rank` / `ts_rank_cd` | **`ts_rank` com pesos A=nome, B=caminho, C=metadados, D=texto, normalização 1** (log do tamanho), para um PDF longo não dominar. Desempate por `effective_date desc`. |
| D11 | Dono na PoC | Sem dono / coluna `owner` | **Coluna `owner text`** com o e-mail vindo de `about.get`. Custa uma coluna e mantém a regra "toda consulta filtra pelo dono" no código que será reaproveitado. Vira `owner_id uuid` na Etapa 1. |
| D12 | Esquema | O script cria as tabelas / SQL aplicado à mão | **`poc/db/schema.sql` aplicado no SQL Editor do Supabase**. O script Python nunca cria esquema, respeitando o contrato de fronteira. Na Etapa 1 esse SQL vira a primeira migração da API. |
| D14 | Driver Postgres no Python | psycopg-binary / pg8000 / cliente oficial do PostgreSQL | **pg8000** (decidido na Tarefa 10). O Smart App Control do Windows passou a bloquear a DLL do psycopg-binary. O pg8000 é Python puro e fica isolado em `extractor/db.py`, para que o worker da Etapa 3, em Linux, possa voltar ao psycopg trocando só esse arquivo. A conexão verifica o certificado se `SUPABASE_CA_CERT` existir; senão, só criptografa, que é o mesmo que o `sslmode=prefer` fazia com o psycopg. |
| D13 | Exposição no Supabase | Esquema `public` exposto / RLS | **Ativar RLS sem nenhuma policy** nas tabelas e dar `revoke execute` de `search_files` para `anon` e `authenticated`. Senão o Data API do Supabase expõe os dados pessoais pela chave anônima. |

## 4. Tarefas em ordem (total ≈ 35,5 h)

| # | Tarefa | h |
|---|---|---|
| 1 | **Registrar as 10 buscas e o gabarito** em `avaliacao/buscas.md` e fazer commit (seção 9). Precisa vir antes de qualquer código de busca. | 1,0 |
| 2 | Configurar o Google Cloud (seção 5) e guardar `credentials.json` fora do git. | 1,5 |
| 3 | Preparar o ambiente: Python 3.12, `.venv`, `requirements.txt` (`google-api-python-client`, `google-auth-oauthlib`, `psycopg[binary]`, `pypdf`, `python-docx`, `requests`, `streamlit`, `python-dotenv`) e `.env.example`. | 1,5 |
| 4 | Criar o projeto no Supabase e o `schema.sql` (extensão, `pt_unaccent`, tabelas, índices, RLS). | 2,0 |
| 5 | `extractor/drive.py`: autenticação com cache em `token.json`, listagem recursiva em largura com montagem do caminho, download e export. | 3,0 |
| 6 | `extractor/metadata.py`: classificar o tipo, ler `imageMediaMetadata`, montar as datas e `effective_date`, normalizar o nome (`_ . -` e camelCase viram espaços). | 2,0 |
| 7 | `extractor/text.py`: PDF, DOCX, TXT (UTF-8 com recuo para cp1252) e export de Google Docs; limites de 50 MB e 200 KB; remoção de `\x00`. | 5,0 |
| 8 | `extractor/geocode.py`: Nominatim com cache em `geocode_cache` (coordenada arredondada em 2 casas, cerca de 1 km), 1 requisição por segundo e User-Agent com e-mail. | 2,5 |
| 9 | `extractor/store.py` e `index_folder.py`: upsert, pular arquivo sem mudança, checar o tamanho do banco e imprimir o relatório final. | 3,0 |
| 10 | Rodar a indexação completa na pasta real e corrigir as falhas encontradas. | 3,0 |
| 11 | Função SQL `search_files` com recuo AND→OU e trecho com `ts_headline`, e os testes dos critérios 4 a 7. | 3,0 |
| 12 | `search_app.py` em Streamlit: busca, filtros de ano e tipo, lista numerada. | 3,0 |
| 13 | Sessão de avaliação: 10 buscas × 2 ferramentas, gravadas, e preencher `resultados.csv`. | 2,5 |
| 14 | `avaliacao/relatorio.md`: números, análise das derrotas e decisão do portão. | 1,5 |

Folga de ~4,5 h até o teto de 40 h, que absorve a tarefa 10 (a pasta real sempre
surpreende).

**Estrutura** (o `poc/` fica isolado; como organizar o monorepo é decisão da Etapa 1):
```
biographai/
  escopo.md  prompts-planos.md  docs/etapa-0-poc.md  .gitignore
  poc/
    db/schema.sql
    extractor/            # REAPROVEITADO na Etapa 3: funções puras, sem fila e sem UI
      drive.py  metadata.py  text.py  geocode.py  searchdoc.py  store.py
    index_folder.py       # CLI que orquestra o extractor
    search_app.py         # DESCARTÁVEL
    requirements.txt  .env.example
  avaliacao/
    buscas.md  resultados.csv  relatorio.md
```

## 5. Configuração no Google Cloud (passo a passo)

1. Em **console.cloud.google.com**, criar o projeto `biographai-poc`.
2. Em **APIs e serviços > Biblioteca**, ativar a **Google Drive API**.
3. Em **Google Auth Platform > Branding** (antiga "Tela de consentimento OAuth"),
   preencher o nome do app `biograph.IA (PoC)`, o e-mail de suporte e o e-mail de
   contato do desenvolvedor. Logo e domínios não são necessários em modo de teste.
4. Em **Público (Audience)**:
   - O tipo de usuário é **Externo**. Conta Gmail pessoal não tem a opção "Interno".
   - O status de publicação fica **Em teste**. Não publicar.
   - Em **Usuários de teste > Add users**, adicionar o **seu próprio Gmail**. Em modo de
     teste, só quem está na lista consegue autorizar, com limite de 100 pessoas. Para
     incluir outro avaliador depois, basta adicionar o e-mail dele aqui.
5. Em **Acesso a dados (Data Access) > Adicionar ou remover escopos**, incluir só
   `https://www.googleapis.com/auth/drive.readonly`. O console marca esse escopo como
   restrito; em modo de teste isso não bloqueia nada.
6. Em **Clientes > Criar cliente**, escolher o tipo **App para computador**, baixar o JSON
   e salvar como `poc/credentials.json` (está no `.gitignore`).
7. Na primeira execução do `index_folder.py`, o navegador abre e mostra o aviso "O Google
   não verificou este app". Clicar em *Avançado > Acessar biograph.IA (não seguro)* e
   autorizar. O token fica em `poc/token.json`.
8. **Atenção:** em modo de teste, o *refresh token* expira em **7 dias**. Depois disso,
   apague o `token.json` e autorize de novo. O script mostra essa instrução quando
   recebe `RefreshError`.

## 6. Contratos

### 6.1 Tabelas (`poc/db/schema.sql`)
```sql
create extension if not exists unaccent;
create text search configuration pt_unaccent (copy = portuguese);
alter text search configuration pt_unaccent
  alter mapping for hword, hword_part, word with unaccent, portuguese_stem;

create table files (
  id                    uuid primary key default gen_random_uuid(),
  owner                 text not null,          -- e-mail Google; vira owner_id uuid na Etapa 1
  drive_file_id         text not null,
  name                  text not null,
  name_search           text not null,          -- nome normalizado: "IMG_2019-03" -> "IMG 2019 03"
  path                  text not null,          -- "Meu Drive/Documentos/Casa"
  mime_type             text not null,
  kind                  text not null check (kind in ('jpg','png','pdf','docx','txt','gdoc')),
  size_bytes            bigint,
  web_view_link         text not null,
  drive_created_at      timestamptz,
  drive_modified_at     timestamptz,
  captured_at           timestamptz,            -- EXIF, via imageMediaMetadata
  doc_created_at        timestamptz,            -- metadado interno do PDF ou DOCX
  effective_date        timestamptz,
  effective_date_source text check (effective_date_source in ('exif','documento','drive')),
  city                  text,
  state                 text,
  metadata              jsonb not null default '{}',   -- câmera, lat/lon, nº de páginas...
  search_meta           text,                   -- "Florianópolis SC Apple iPhone 12 março 2019"
  extracted_text        text,                   -- no máximo 200 KB
  text_truncated        boolean not null default false,
  search_vector tsvector generated always as (
      setweight(to_tsvector('pt_unaccent', coalesce(name_search,'')),    'A') ||
      setweight(to_tsvector('pt_unaccent', coalesce(path,'')),           'B') ||
      setweight(to_tsvector('pt_unaccent', coalesce(search_meta,'')),    'C') ||
      setweight(to_tsvector('pt_unaccent', coalesce(extracted_text,'')), 'D')
  ) stored,
  status                text not null check (status in ('ok','sem_texto','erro')),
  error                 text,
  indexed_at            timestamptz not null default now(),
  unique (owner, drive_file_id)
);
create index files_search_idx on files using gin (search_vector);
create index files_owner_date_idx on files (owner, effective_date desc);
create index files_owner_kind_idx on files (owner, kind);

create table geocode_cache (
  lat_r numeric(5,2), lon_r numeric(5,2),
  city text, state text, raw jsonb,
  primary key (lat_r, lon_r)
);
alter table files enable row level security;          -- sem policies = fechado para o Data API
alter table geocode_cache enable row level security;
```

### 6.2 Função de busca (a tela chama só esta função)
```sql
search_files(p_owner text, p_q text, p_year int default null,
             p_kind text[] default null, p_limit int default 50)
returns table (pos int, id uuid, name text, path text, kind text,
               effective_date timestamptz, effective_date_source text,
               city text, state text, web_view_link text, rank real,
               snippet text, match_mode text)   -- match_mode: 'and' | 'or' | 'lista'
```
- Com `p_q` vazio, lista por `effective_date desc` aplicando os filtros.
- O filtro de ano é `effective_date >= make_date(p_year,1,1)` e
  `< make_date(p_year+1,1,1)`, para usar o índice.
- `revoke execute on function search_files from anon, authenticated;`

### 6.3 Assinaturas Python (`extractor/`, reaproveitado)
```python
# drive.py
def get_service(credentials_path: Path, token_path: Path) -> Resource
def get_owner_email(svc) -> str
def list_tree(svc, root_id: str) -> Iterator[DriveItem]   # BFS; DriveItem inclui path
def download(svc, file_id: str, max_bytes: int) -> bytes | None   # None se acima do limite
def export_gdoc_text(svc, file_id: str) -> str

# metadata.py
def classify(mime_type: str, name: str) -> Kind | None     # None = ignorado
def from_drive_item(item: DriveItem) -> FileMeta           # datas, GPS, câmera, name_search

# text.py  (funções puras: bytes -> texto; sem rede e sem banco)
def extract_pdf(data: bytes) -> TextResult                 # TextResult(text, doc_created_at, pages, truncated)
def extract_docx(data: bytes) -> TextResult
def extract_txt(data: bytes) -> TextResult
def clamp_text(text: str, max_bytes: int = 200_000) -> tuple[str, bool]

# geocode.py
def reverse(conn, lat: float, lon: float) -> Place | None  # cache primeiro, depois 1 req/s

# searchdoc.py
def build_search_meta(meta: FileMeta, place: Place | None) -> str   # inclui mês e ano por extenso

# store.py
def is_unchanged(conn, owner: str, drive_file_id: str, modified: datetime) -> bool
def upsert_file(conn, record: FileRecord) -> None
def db_size_bytes(conn) -> int
```

### 6.4 CLI e tela
- `python index_folder.py --folder <id|root> [--limit N] [--reprocess-errors]`. Os
  segredos vêm do `.env` (`DATABASE_URL` do Session pooler e `NOMINATIM_EMAIL`).
- O relatório final mostra:
  - arquivos listados, suportados e ignorados (por mimeType);
  - quantos terminaram em `ok`, `sem_texto` e `erro`;
  - quantos foram pulados por não terem mudado;
  - duração da execução;
  - tamanho do banco e bytes médios por arquivo.
- `streamlit run search_app.py` abre uma tela com:
  - campo de busca;
  - seletor de ano (anos existentes no índice, mais "Todos");
  - seleção múltipla de tipo (Foto = jpg+png, PDF, Word, Texto, Google Docs);
  - total de resultados e o `match_mode`;
  - lista **numerada** com nome (link para `web_view_link`), caminho, data com a origem
    ("data da foto", "data do documento", "data no Drive"), cidade e trecho do texto.

## 7. Casos de erro

| Caso | Tratamento |
|---|---|
| Token expirado (7 dias em modo de teste) ou revogado | Captura `RefreshError` e mostra "apague poc/token.json e rode de novo". |
| 403 `rateLimitExceeded` ou `userRateLimitExceeded`, 429, 5xx do Drive | `execute(num_retries=5)`, que já aplica backoff exponencial no cliente Google. |
| Arquivo acima de 50 MB | Não baixa. Indexa nome e metadados com `status='sem_texto'` e `error='acima de 50 MB'`. |
| PDF criptografado ou corrompido, DOCX inválido | `try/except` por arquivo, grava `status='erro'` com a mensagem, e o lote segue. `--reprocess-errors` tenta de novo. |
| PDF escaneado (menos de ~100 caracteres extraídos) | `status='sem_texto'`. O OCR é da P1. |
| Export de Google Doc acima de 10 MB (`exportSizeLimitExceeded`) | `status='sem_texto'`. |
| Texto acima de 200 KB | Corta na fronteira de caractere UTF-8 e marca `text_truncated=true`. |
| `\x00` ou caracteres de controle no texto (o Postgres recusa) | Remove antes do upsert. |
| TXT com codificação desconhecida | Tenta UTF-8, depois cp1252 e por fim latin-1 com `errors='replace'`. |
| Nominatim com 429, timeout ou sem resultado | Deixa a cidade em `null`. Guarda "sem resultado" no cache, mas não guarda erro. O arquivo continua `ok`. |
| Atalhos, lixeira, Sheets, Slides, vídeo, áudio | Filtra `trashed=false` e ignora o resto, contando no relatório. |
| Conexão com o pooler cai no meio | O script aborta. Como é retomável (pula o que não mudou), basta rodar de novo. |
| Banco perto de 500 MB | `db_size_bytes` a cada 200 arquivos; para em 400 MB com uma mensagem. |
| Projeto do Supabase pausado (1 semana sem uso) | Restaurar no painel antes da sessão de avaliação; está no checklist da tarefa 13. |
| Busca sem resultado com AND | Repete em OU. Se continuar vazio, mostra "Nada encontrado". |

## 8. Critérios de aceite

1. `git log` mostra o commit de `avaliacao/buscas.md` (10 buscas com gabarito)
   **antes** do commit que cria `search_files` e `search_app.py`.
2. `index_folder.py` termina a pasta escolhida com o relatório impresso, e no máximo 5%
   dos arquivos suportados ficam com `status='erro'`.
3. Rodar de novo sem mudanças no Drive processa 0 arquivos (todos pulados) e não cria
   duplicatas (`unique (owner, drive_file_id)`).
4. Em 5 documentos sorteados (PDF, DOCX e Google Docs), uma frase de dentro do texto que
   não aparece no nome devolve o arquivo entre os 3 primeiros.
5. As variações de escrita funcionam: `certidao` encontra "Certidão", e `contratos`
   encontra "contrato".
6. Uma foto JPG com GPS aparece ao buscar o nome da cidade. O filtro de ano só devolve
   arquivos cuja `effective_date` cai naquele ano. O filtro de tipo só devolve os tipos
   marcados.
7. `explain analyze` de `search_files` com texto e filtros roda em menos de 300 ms no
   acervo indexado.
8. O relatório mostra os bytes médios por arquivo, que é a entrada para revisar a conta
   de 5 KB por arquivo do escopo.
9. `avaliacao/resultados.csv` tem as 14 linhas (7 buscas × 2 ferramentas) e
   `relatorio.md` traz a decisão do portão.
10. `git ls-files` não contém `credentials.json`, `token.json` nem `.env`.

A etapa está **concluída** quando a medição é feita, qualquer que seja o resultado.
Perder para o Drive é um resultado válido da PoC.

## 9. Protocolo de avaliação

**Viés declarado:** quem constrói é quem avalia, e o portão em `prompts-planos.md` pede
"alguém que não seja você". Para compensar:

- **Congelar antes.** As 10 buscas e o gabarito vão para o commit na tarefa 1, antes de
  existir código de busca. Depois disso, não se ajusta ranqueamento pensando nelas.
- **Buscas reais, não escolhidas a dedo.**
  - Anotar ao longo de 2 ou 3 dias as vezes em que você realmente precisou achar algo no
    Drive, ou lembrar de 10 arquivos que já precisou achar.
  - Descrever de memória, sem abrir o Drive.
  - Não escolher pensando no que o app faz bem. Registrar a distribuição de tipos como
    ela sair.
- **Gabarito.** Só depois de escrever a descrição, localizar o arquivo navegando pelas
  pastas (sem usar a busca) e anotar o `drive_file_id`. O arquivo precisa estar dentro
  da pasta raiz indexada. Se não estiver, troque a busca antes do commit.
- **Formato de `buscas.md`:** id, descrição do que se procura, primeira consulta exata
  (a mesma nas duas ferramentas), tipo esperado, id e caminho do alvo.
- **Campos de diagnóstico (não entram no placar):**
  - *Consulta descritiva*: como o avaliador gostaria de buscar. Roda só no app, numa
    rodada separada, depois das 20 medições.
  - *Sei o nome do arquivo?* (sim/não): o relatório separa as vitórias por esse
    campo, porque buscas pelo nome conhecido tendem a empatar.

**Condução (tarefa 13):**
- Na véspera, confirmar que o Supabase está ativo e o `token.json` é válido, e fazer uma
  reindexação.
- Drive nativo: usar drive.google.com no navegador, restrito à mesma pasta. Com "Meu
  Drive" como raiz, basta a busca normal. Com outra pasta, usar a busca avançada em
  *Localização*. Os filtros nativos (tipo, data) são permitidos.
- Nosso app: a tela Streamlit, com os filtros de ano e tipo permitidos.
- **A ordem alterna:** nas buscas ímpares, o Drive vem primeiro; nas pares, o app. Isso
  compensa o efeito de aprendizado (depois de achar numa ferramenta, você lembra o
  nome).
- A tentativa 1 é sempre a consulta congelada. Depois podem vir até 2 reformulações
  livres, somando no máximo **3 tentativas e 120 s por ferramenta**.
- Gravar a tela (`Win+Alt+R`) e cronometrar a partir da gravação, do primeiro caractere
  digitado até o clique no alvo.

**O que se mede** (em `resultados.csv`: `busca_id, ferramenta, ordem, achou, tentativas, tempo_s, posicao, consulta_final, obs`):
- **achou:** o alvo foi clicado em até 3 tentativas e 120 s.
- **tempo_s:** segundos até o clique, ou 120 se não achou.
- **posicao:** posição do alvo na lista da tentativa que achou, contando a partir de 1.
  É diagnóstico e não entra no placar.

**Quem vence cada busca** (regras aplicadas em ordem):
1. Só uma ferramenta achou: ela vence.
2. As duas acharam: vence quem usou menos tentativas.
3. Mesmo número de tentativas: vence quem foi pelo menos 25% **e** 5 s mais rápida.
   Senão, empate.
4. Nenhuma achou: empate, anotado como "lacuna das duas".

## 10. Critério de corte

"Acerto" é o app achar o alvo em até 3 tentativas e 120 s. A regra segue o portão de
`prompts-planos.md` e acrescenta um piso de acertos.

O conjunto final tem **7 buscas**, por decisão do avaliador (veja `avaliacao/buscas.md`).
Os limites mantêm as proporções do portão original (60% de vitórias e 70% de acertos
para seguir; 30% de vitórias ou 50% de acertos para parar):

| Resultado com 7 buscas | Decisão |
|---|---|
| App vence **≥ 5** e acerta **≥ 5** | A tese se sustenta. Seguir para a Etapa 1. |
| App vence **3 ou 4**, ou acerta **4** | Investigar as derrotas (extração, ranqueamento ou tipo de arquivo), corrigir e repetir **uma vez** com buscas novas, congeladas do mesmo jeito. |
| App vence **≤ 2**, ou acerta **≤ 3** | **A tese não se sustenta.** O problema é de tese, não de execução. Reavaliar o cenário antes de gastar as 400 h. |

O piso de acertos existe porque ganhar do Drive achando só metade dos arquivos não
entrega produto. O H1 pede 80% com contexto; sem contexto, 70% é o mínimo razoável.

**Previsão registrada antes do teste:** 4 das 7 buscas são fotos sem nome conhecido
(B02, B03, B06, B07), e a PoC não vê o conteúdo da imagem nem tem contexto do
usuário. A expectativa é de 3 ou 4 acertos. Se isso se confirmar, o relatório deve
separar "falha da tese" de "falha por falta de contexto ou IA em fotos", o que é
argumento para a Etapa 5 ou a Fase 2 no portão de decisão.

**Recomendação:** se o resultado cair perto das fronteiras (4 ou 5 vitórias), repita
com outra pessoa antes da Etapa 1. Custa cerca de 3 h: adicionar o e-mail dela como
usuária de teste, indexar a pasta dela e fazer a sessão.

## 11. Fora desta etapa

- Login, convite e multiusuário. Tabelas `users` e `google_connections`.
- API Fastify, front React/PWA, deploy e Cloudflare.
- Fila pg-boss e worker como serviço. A PoC é um script que roda até o fim.
- Contexto do usuário, edição em massa e miniaturas.
- Verificação de existência antes de exibir, e sincronização incremental pela Changes
  API.
- OCR, DOC antigo, Sheets, Slides, vídeo, áudio e drives compartilhados.
- Filtros de cidade e pasta na tela. A cidade e a pasta entram só no texto pesquisável.
- Reconhecimento de períodos escritos ("março de 2024"). Mês e ano por extenso entram
  só como palavras no campo de metadados.
- `pg_trgm` para erros de digitação.
- Teto de 2.000 arquivos e limites por usuário guardados em configuração.
- Testes automatizados.
- Tratamento de erro elaborado.

## 12. Impactos na Fase 2 (IA)

- **Legenda no mesmo campo:** entra como coluna nova `ai_caption` e uma migração que
  recria a coluna gerada `search_vector` incluindo a legenda (peso B ou C). O Postgres
  recalcula tudo sem reprocessar os arquivos do Drive.
- **Fotos não baixadas (D5):** a legenda precisa dos pixels. Na Fase 2, o worker ganha um
  passo de download da imagem ou do `thumbnailLink`. Como o `extractor/` é feito de
  funções puras por formato, `caption_image(data) -> str` entra como mais uma função.
- **Escopo `drive.readonly` (D3):** é o mesmo de que a Fase 2 precisa, então a
  verificação do Google é feita uma vez só.
- **Bytes por arquivo (critério 8):** é a medida real que define quanto sobra dos 500 MB
  para vetores do `pgvector`, e portanto a dimensão e quantos arquivos recebem vetor.
- **As 10 buscas congeladas** viram o conjunto de regressão da Etapa 4 e o teste da
  Fase 2: a busca por significado precisa ganhar da busca por palavra nelas.
- **Dados no Supabase (D1):** a PoC já coloca dados pessoais em um provedor terceiro.
  Nas duas fases, a região do projeto é uma decisão em aberto (escopo §13).

## 13. Limitações conhecidas da busca (encontradas na Tarefa 11, para a Etapa 4)

Ficam registradas e **não foram corrigidas** depois do congelamento das buscas, para
não ajustar a busca de olho na avaliação.

- **Singular e plural em -ão/-ões/-ães e -m/-ns.** O radical do Postgres não junta essas
  formas, com ou sem acento: "certidões" não casa com `certidao`, "declarações" não casa
  com `declaracao`, "viagem" não casa com `viagens`. Num teste com 30 pares, 22 casaram
  na ordem atual (sem acento antes do radical) e 20 na ordem inversa.
  - *Etapa 4:* expandir a consulta com as variantes de singular e plural, ou usar um
    dicionário como o Hunspell pt_BR.
- **Palavras dentro de URL e e-mail.** O parser guarda `www.unicesumar.edu.br` como um
  token só, então buscar `unicesumar` não acha o documento.
  - *Etapa 4:* trocar `. / @ :` por espaço antes de gerar o vetor.
- **Documentos-modelo repetidos** (21 notas fiscais quase iguais). Nenhuma palavra
  distingue uma da outra; o que as separa são números e valores, e o ranqueamento entre
  elas é praticamente aleatório.
  - *Etapa 4:* indexar números relevantes (valores, datas, CNPJ) e os filtros de
    período e pasta.

Corrigido na Tarefa 11, porque é bug de extração e não de ranqueamento: as **ligaduras
de PDF** (`ﬁ`, `ﬂ`, `ﬀ`, e `Ɵ`/`Ʃ` do Calibri) apareciam em 6 documentos e quebravam
palavras como "identificação" e "normativa".

## Verificação (depois da implementação, quando você pedir)

- Ambiente: `poc/.venv/Scripts/python --version` mostra 3.14 e `pip install -r poc/requirements.txt`
  instala sem erro.
- Banco: `schema.sql` aplicado no SQL Editor, e
  `select to_tsvector('pt_unaccent','Certidões')` devolve `'certido'`.
- Indexação:
  - `python poc/index_folder.py --folder root --limit 50` roda como teste de fumaça;
  - depois, a execução completa com o relatório;
  - por fim, uma segunda execução, que deve pular tudo.
- Busca: rodar os critérios 4 a 7 no SQL Editor e na tela Streamlit.
- Avaliação: seção 9, e o resultado em `avaliacao/relatorio.md`.
