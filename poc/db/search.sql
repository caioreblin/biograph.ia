-- biograph.IA — PoC (Etapa 0): função de busca.
-- Aplicada à mão, como o schema.sql. Pode ser rodada de novo (create or replace).
--
-- Texto: websearch_to_tsquery (E entre os termos); sem resultado, repete com OU.
-- Ranqueamento: ts_rank com pesos A=nome 1.0, B=caminho 0.4, C=metadados 0.2,
-- D=texto 0.1, normalização 1 (divide por 1 + log do tamanho) para documento longo
-- não dominar. Desempate pela data mais recente.
-- Sem texto: lista pelos filtros, da data mais recente para a mais antiga.

create or replace function public.search_files(
  p_owner text,
  p_q     text,
  p_year  int    default null,
  p_kind  text[] default null,
  p_limit int    default 50
)
returns table (
  pos                   int,
  id                    uuid,
  name                  text,
  path                  text,
  kind                  text,
  effective_date        timestamptz,
  effective_date_source text,
  city                  text,
  state                 text,
  web_view_link         text,
  rank                  real,
  snippet               text,
  match_mode            text      -- 'and' | 'or' | 'lista'
)
language plpgsql
stable
set search_path = public
as $$
#variable_conflict use_column
declare
  v_from timestamptz;
  v_to   timestamptz;
  v_q    tsquery;
  v_mode text := 'and';
begin
  -- Ano no fuso do acervo; intervalo semiaberto para usar o índice por data.
  if p_year is not null then
    v_from := make_timestamptz(p_year, 1, 1, 0, 0, 0, 'America/Sao_Paulo');
    v_to   := make_timestamptz(p_year + 1, 1, 1, 0, 0, 0, 'America/Sao_Paulo');
  end if;

  if coalesce(btrim(p_q), '') = '' then
    return query
      select (row_number() over (order by f.effective_date desc nulls last))::int,
             f.id, f.name, f.path, f.kind, f.effective_date, f.effective_date_source,
             f.city, f.state, f.web_view_link, null::real, null::text, 'lista'::text
        from files f
       where f.owner = p_owner
         and (p_kind is null or f.kind = any (p_kind))
         and (v_from is null or (f.effective_date >= v_from and f.effective_date < v_to))
       order by f.effective_date desc nulls last
       limit p_limit;
    return;
  end if;

  v_q := websearch_to_tsquery('pt_unaccent', p_q);
  if numnode(v_q) = 0 then  -- só palavras vazias ("de", "dos"...)
    return;
  end if;

  if not exists (
    select 1 from files f
     where f.owner = p_owner
       and (p_kind is null or f.kind = any (p_kind))
       and (v_from is null or (f.effective_date >= v_from and f.effective_date < v_to))
       and f.search_vector @@ v_q
  ) then
    v_q := replace(v_q::text, ' & ', ' | ')::tsquery;
    v_mode := 'or';
  end if;

  return query
    with hits as (
      select f.*, ts_rank(f.search_vector, v_q, 1) as r
        from files f
       where f.owner = p_owner
         and (p_kind is null or f.kind = any (p_kind))
         and (v_from is null or (f.effective_date >= v_from and f.effective_date < v_to))
         and f.search_vector @@ v_q
       order by r desc, f.effective_date desc nulls last
       limit p_limit
    )
    select (row_number() over (order by h.r desc, h.effective_date desc nulls last))::int,
           h.id, h.name, h.path, h.kind, h.effective_date, h.effective_date_source,
           h.city, h.state, h.web_view_link, h.r,
           case when h.extracted_text is not null then
             ts_headline('pt_unaccent', h.extracted_text, v_q,
                         'MaxWords=25, MinWords=8, MaxFragments=2, FragmentDelimiter=" … ", StartSel=«, StopSel=»')
           end,
           v_mode
      from hits h
     order by 1;
end
$$;

-- Fechar para o Data API do Supabase (RPC via chave anon/authenticated).
revoke execute on function public.search_files(text, text, int, text[], int) from public, anon, authenticated;
