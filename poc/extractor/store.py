"""Gravação na tabela files. O esquema é de quem cuida das migrações; aqui só DML."""

from dataclasses import dataclass
from datetime import datetime

from .db import Connection, jsonb
from .geocode import Place
from .metadata import DateSource, FileMeta

@dataclass
class FileRecord:
    owner: str
    meta: FileMeta
    status: str  # 'ok' | 'sem_texto' | 'erro'
    effective_date: datetime
    effective_date_source: DateSource
    search_meta: str
    text: str | None = None
    text_truncated: bool = False
    doc_created_at: datetime | None = None
    place: Place | None = None
    error: str | None = None
    extra_metadata: dict | None = None  # ex.: nº de páginas

def load_index_state(conn: Connection, owner: str) -> dict[str, tuple[datetime, str]]:
    """drive_file_id -> (drive_modified_at, status) do que já está indexado."""
    rows = conn.execute(
        "select drive_file_id, drive_modified_at, status from files where owner = %s", (owner,)
    ).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}

_UPSERT = """
insert into files (
  owner, drive_file_id, name, name_search, path, mime_type, kind, size_bytes, web_view_link,
  drive_created_at, drive_modified_at, captured_at, doc_created_at,
  effective_date, effective_date_source, city, state, metadata, search_meta,
  extracted_text, text_truncated, status, error, indexed_at
) values (
  %(owner)s, %(drive_file_id)s, %(name)s, %(name_search)s, %(path)s, %(mime_type)s, %(kind)s,
  %(size_bytes)s, %(web_view_link)s, %(drive_created_at)s, %(drive_modified_at)s, %(captured_at)s,
  %(doc_created_at)s, %(effective_date)s, %(effective_date_source)s, %(city)s, %(state)s,
  %(metadata)s::jsonb, %(search_meta)s, %(extracted_text)s, %(text_truncated)s, %(status)s, %(error)s, now()
)
on conflict (owner, drive_file_id) do update set
  name = excluded.name, name_search = excluded.name_search, path = excluded.path,
  mime_type = excluded.mime_type, kind = excluded.kind, size_bytes = excluded.size_bytes,
  web_view_link = excluded.web_view_link, drive_created_at = excluded.drive_created_at,
  drive_modified_at = excluded.drive_modified_at, captured_at = excluded.captured_at,
  doc_created_at = excluded.doc_created_at, effective_date = excluded.effective_date,
  effective_date_source = excluded.effective_date_source, city = excluded.city,
  state = excluded.state, metadata = excluded.metadata, search_meta = excluded.search_meta,
  extracted_text = excluded.extracted_text, text_truncated = excluded.text_truncated,
  status = excluded.status, error = excluded.error, indexed_at = now()
"""

def upsert_file(conn: Connection, rec: FileRecord) -> None:
    m = rec.meta
    metadata = {**m.metadata, **(rec.extra_metadata or {})}
    if rec.place and rec.place.state_code:
        metadata["state_code"] = rec.place.state_code
    conn.execute(_UPSERT, {
        "owner": rec.owner, "drive_file_id": m.drive_file_id, "name": m.name,
        "name_search": m.name_search, "path": m.path, "mime_type": m.mime_type, "kind": m.kind,
        "size_bytes": m.size, "web_view_link": m.web_view_link,
        "drive_created_at": m.drive_created_at, "drive_modified_at": m.drive_modified_at,
        "captured_at": m.captured_at, "doc_created_at": rec.doc_created_at,
        "effective_date": rec.effective_date, "effective_date_source": rec.effective_date_source,
        "city": rec.place and rec.place.city, "state": rec.place and rec.place.state,
        "metadata": jsonb(metadata), "search_meta": rec.search_meta,
        "extracted_text": rec.text, "text_truncated": rec.text_truncated,
        "status": rec.status, "error": rec.error,
    })

def delete_missing(conn: Connection, owner: str, seen_ids: set[str]) -> int:
    """Remove o que não apareceu na listagem completa (apagado, movido ou na lixeira)."""
    cur = conn.execute(
        "delete from files where owner = %s and not (drive_file_id = any(%s::text[]))",
        (owner, list(seen_ids)),
    )
    return cur.rowcount

def db_size_bytes(conn: Connection) -> int:
    return conn.execute("select pg_database_size(current_database())").fetchone()[0]

def files_size_stats(conn: Connection, owner: str) -> tuple[int, int]:
    """(nº de arquivos do dono, bytes da tabela files com índices e TOAST)."""
    return conn.execute(
        "select (select count(*) from files where owner = %s), pg_total_relation_size('files')",
        (owner,),
    ).fetchone()
