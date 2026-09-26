-- biograph.IA — PoC (Etapa 0)
-- Esquema aplicado à mão (SQL Editor do Supabase). O script Python NUNCA cria esquema.
-- Na Etapa 1 este arquivo vira a primeira migração da API.
-- Pode ser rodado de novo sem erro (idempotente).

-- ---------------------------------------------------------------------------
-- Busca em português sem acento
-- ---------------------------------------------------------------------------
-- No Supabase as extensões ficam no schema "extensions".
create extension if not exists unaccent with schema extensions;

do $$
begin
  if not exists (select 1 from pg_ts_config where cfgname = 'pt_unaccent') then
    create text search configuration public.pt_unaccent (copy = pg_catalog.portuguese);
    alter text search configuration public.pt_unaccent
      alter mapping for hword, hword_part, word
      with extensions.unaccent, portuguese_stem;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- Arquivos indexados
-- ---------------------------------------------------------------------------
create table if not exists public.files (
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
      setweight(to_tsvector('public.pt_unaccent'::regconfig, coalesce(name_search, '')),    'A') ||
      setweight(to_tsvector('public.pt_unaccent'::regconfig, coalesce(replace(path, '/', ' '), '')), 'B') ||
      setweight(to_tsvector('public.pt_unaccent'::regconfig, coalesce(search_meta, '')),    'C') ||
      setweight(to_tsvector('public.pt_unaccent'::regconfig, coalesce(extracted_text, '')), 'D')
  ) stored,
  status                text not null check (status in ('ok','sem_texto','erro')),
  error                 text,
  indexed_at            timestamptz not null default now(),
  unique (owner, drive_file_id)
);

create index if not exists files_search_idx     on public.files using gin (search_vector);
create index if not exists files_owner_date_idx on public.files (owner, effective_date desc);
create index if not exists files_owner_kind_idx on public.files (owner, kind);

-- ---------------------------------------------------------------------------
-- Cache de geocodificação reversa (Nominatim), por coordenada arredondada (~1 km)
-- ---------------------------------------------------------------------------
create table if not exists public.geocode_cache (
  lat_r      numeric(5,2) not null,
  lon_r      numeric(5,2) not null,
  city       text,                              -- null = consultado e sem resultado
  state      text,
  raw        jsonb,
  created_at timestamptz not null default now(),
  primary key (lat_r, lon_r)
);

-- ---------------------------------------------------------------------------
-- Fechar para o Data API do Supabase (chave anon/authenticated).
-- A PoC conecta direto no Postgres com o usuário "postgres", que ignora RLS.
-- ---------------------------------------------------------------------------
alter table public.files         enable row level security;
alter table public.geocode_cache enable row level security;
revoke all on public.files, public.geocode_cache from anon, authenticated;
