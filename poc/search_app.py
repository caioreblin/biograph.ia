"""Tela de busca da PoC (descartável). Rodar com: streamlit run search_app.py

Só chama a função search_files do banco; nenhuma chave vai para o navegador.
"""

import os
import re
import time
from datetime import timedelta, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from extractor import db

HERE = Path(__file__).resolve().parent
LOCAL_TZ = timezone(timedelta(hours=-3))
LIMIT = 50

KIND_LABELS = {
    "Foto": ["jpg", "png"],
    "PDF": ["pdf"],
    "Word": ["docx"],
    "Texto": ["txt"],
    "Google Docs": ["gdoc"],
}
KIND_NAMES = {"jpg": "Foto", "png": "Foto", "pdf": "PDF", "docx": "Word", "txt": "Texto", "gdoc": "Google Docs"}
DATE_SOURCE = {"exif": "data da foto", "documento": "data do documento", "drive": "data no Drive"}
MODE_LABEL = {"and": "todas as palavras", "or": "qualquer palavra", "lista": "sem texto, só filtros"}

SEARCH_SQL = "select * from search_files(%s, %s, %s::int, %s::text[], %s::int)"


@st.cache_resource
def get_conn() -> db.Connection:
    load_dotenv(HERE / ".env")
    return db.connect(
        os.environ["DATABASE_URL"], HERE / os.getenv("SUPABASE_CA_CERT", "supabase-ca.crt")
    )


def run(sql: str, params: tuple = ()) -> list:
    try:
        return get_conn().execute(sql, params).fetchall()
    except (db.Error, OSError):  # conexão caiu (pooler, rede): reconecta uma vez
        get_conn.clear()
        return get_conn().execute(sql, params).fetchall()


@st.cache_data(ttl=600)
def owner_and_years() -> tuple[str, list[int]]:
    owners = [r[0] for r in run("select distinct owner from files")]
    if len(owners) != 1:
        raise RuntimeError(f"Esperava um dono no índice, encontrei {len(owners)}.")
    years = [r[0] for r in run(
        "select distinct extract(year from effective_date at time zone 'America/Sao_Paulo')::int y "
        "from files where owner = %s and effective_date is not null order by y desc",
        (owners[0],),
    )]
    return owners[0], years


def md_escape(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$])", r"\\\1", text)


def snippet_md(snippet: str | None) -> str | None:
    if not snippet or "«" not in snippet:
        return None
    return md_escape(" ".join(snippet.split())).replace("«", "**").replace("»", "**")


st.set_page_config(page_title="biograph.IA — busca", layout="centered")
st.title("biograph.IA · busca")

owner, years = owner_and_years()

q = st.text_input("Buscar", placeholder="nome, assunto, cidade, mês…", label_visibility="collapsed")
col_year, col_kind = st.columns([1, 3])
year_label = col_year.selectbox("Ano", ["Todos"] + [str(y) for y in years])
kind_labels = col_kind.multiselect("Tipo", list(KIND_LABELS), placeholder="Todos os tipos")

year = None if year_label == "Todos" else int(year_label)
kinds = [k for label in kind_labels for k in KIND_LABELS[label]] or None

t0 = time.perf_counter()
rows = run(SEARCH_SQL, (owner, q, year, kinds, LIMIT))
elapsed_ms = (time.perf_counter() - t0) * 1000

if not rows:
    st.info("Nada encontrado.")
    st.stop()

mode = rows[0][12]
more = " (mostrando os primeiros)" if len(rows) == LIMIT else ""
st.caption(f"{len(rows)} resultados{more} · {MODE_LABEL[mode]} · {elapsed_ms:.0f} ms")

for pos, _id, name, path, kind, eff_date, date_src, city, state, link, _rank, snippet, _mode in rows:
    meta = [KIND_NAMES[kind], md_escape(path)]
    if eff_date:
        meta.append(f"{eff_date.astimezone(LOCAL_TZ):%d/%m/%Y} ({DATE_SOURCE[date_src]})")
    if city:
        meta.append(md_escape(f"{city}/{state}" if state else city))
    st.markdown(f"**{pos}.** [{md_escape(name)}]({link})  \n<small>{' · '.join(meta)}</small>",
                unsafe_allow_html=True)
    if (s := snippet_md(snippet)) is not None:
        st.markdown(f"<small>… {s} …</small>", unsafe_allow_html=True)
