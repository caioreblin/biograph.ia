"""Indexa uma pasta do Google Drive (recursivamente) na tabela files.

Uso:
  python index_folder.py [--folder root|<id>] [--limit N] [--reprocess-errors] [--force]

Retomável: arquivos que não mudaram no Drive desde a última execução são pulados.
"""

import argparse
import os
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from extractor import db, drive, geocode
from extractor import metadata as md
from extractor import text as tx
from extractor.searchdoc import build_search_meta
from extractor.store import (
    FileRecord, db_size_bytes, delete_missing, files_size_stats, load_index_state, upsert_file,
)

HERE = Path(__file__).resolve().parent
SIZE_CHECK_EVERY = 200
PROGRESS_EVERY = 25

def extract_text(svc, meta: md.FileMeta, max_download: int, max_text: int):
    """(TextResult | None, status, error) para um arquivo suportado."""
    if meta.kind in ("jpg", "png"):
        return None, "ok", None
    if meta.kind == "gdoc":
        try:
            result = tx.from_plain_text(drive.export_gdoc_text(svc, meta.drive_file_id), max_text)
        except drive.ExportTooLarge:
            return None, "sem_texto", "export do Google Docs acima de 10 MB"
    else:
        data = drive.download(svc, meta.drive_file_id, max_download, meta.size)
        if data is None:
            return None, "sem_texto", f"acima de {max_download // (1024 * 1024)} MB"
        extractor = {"pdf": tx.extract_pdf, "docx": tx.extract_docx, "txt": tx.extract_txt}[meta.kind]
        result = extractor(data, max_text)
    if result.is_textless:
        return result, "sem_texto", "sem texto extraível (provável PDF escaneado)" if result.pages else None
    return result, "ok", None

def build_record(conn, svc, owner: str, meta: md.FileMeta, cfg: dict) -> FileRecord:
    try:
        result, status, error = extract_text(svc, meta, cfg["max_download"], cfg["max_text"])
    except Exception as e:  # arquivo corrompido, PDF com senha etc.: não derruba o lote
        result, status, error = None, "erro", f"{type(e).__name__}: {e}"[:500]

    doc_created = result.doc_created_at if result else None
    date, source = md.effective_date(meta.captured_at, doc_created, meta.drive_created_at, meta.drive_modified_at)
    place = geocode.reverse(conn, meta.lat, meta.lon, cfg["email"]) if meta.lat is not None else None

    return FileRecord(
        owner=owner, meta=meta, status=status, error=error,
        effective_date=date, effective_date_source=source,
        search_meta=build_search_meta(meta, place, date),
        text=result.text if result else None,
        text_truncated=result.truncated if result else False,
        doc_created_at=doc_created,
        place=place,
        extra_metadata={"pages": result.pages} if result and result.pages else None,
    )

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", default="root", help="ID da pasta raiz ('root' = Meu Drive)")
    ap.add_argument("--limit", type=int, help="processa no máximo N arquivos suportados (teste)")
    ap.add_argument("--reprocess-errors", action="store_true", help="tenta de novo os que deram erro")
    ap.add_argument("--force", action="store_true", help="reprocessa tudo, mesmo o que não mudou")
    args = ap.parse_args()

    load_dotenv(HERE / ".env")
    cfg = {
        "email": os.environ["NOMINATIM_EMAIL"],
        "max_download": int(os.getenv("MAX_DOWNLOAD_MB", "50")) * 1024 * 1024,
        "max_text": int(os.getenv("MAX_TEXT_KB", "200")) * 1000,
        "db_stop": int(os.getenv("DB_SIZE_STOP_MB", "400")) * 1024 * 1024,
    }

    try:
        svc = drive.get_service(
            HERE / os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json"),
            HERE / os.getenv("GOOGLE_TOKEN_PATH", "token.json"),
        )
    except drive.AuthError as e:
        print(f"ERRO: {e}")
        return 2
    owner = drive.get_owner_email(svc)

    t0 = time.time()
    listed, supported, processed, skipped = 0, 0, 0, 0
    ignored, statuses = Counter(), Counter()
    seen: set[str] = set()
    stop_reason = None

    ca_cert = HERE / os.getenv("SUPABASE_CA_CERT", "supabase-ca.crt")
    with db.connect(os.environ["DATABASE_URL"], ca_cert) as conn:
        state = load_index_state(conn, owner)
        print(f"Indexando '{args.folder}' de {owner} ({len(state)} arquivos já no índice)")

        for item in drive.list_tree(svc, args.folder):
            listed += 1
            meta = md.from_drive_item(item)
            if meta is None:
                ignored[item.mime_type] += 1
                continue
            if args.limit is not None and supported >= args.limit:
                stop_reason = f"--limit {args.limit}"
                break
            supported += 1
            seen.add(meta.drive_file_id)

            prev = state.get(meta.drive_file_id)
            if (
                not args.force and prev and prev[0] == meta.drive_modified_at
                and not (args.reprocess_errors and prev[1] == "erro")
            ):
                skipped += 1
                continue

            rec = build_record(conn, svc, owner, meta, cfg)
            try:
                upsert_file(conn, rec)
            except db.Error as e:
                rec.status, rec.error, rec.text = "erro", f"falha ao gravar: {e}"[:500], None
                upsert_file(conn, rec)
            statuses[rec.status] += 1
            processed += 1

            if processed % PROGRESS_EVERY == 0:
                print(f"  ... {processed} processados, {skipped} pulados ({time.time() - t0:.0f}s)")
            if processed % SIZE_CHECK_EVERY == 0 and db_size_bytes(conn) >= cfg["db_stop"]:
                stop_reason = f"banco atingiu {cfg['db_stop'] // (1024 * 1024)} MB"
                break

        removed = 0
        if stop_reason is None and args.folder == "root":
            removed = delete_missing(conn, owner, seen)

        n_files, files_bytes = files_size_stats(conn, owner)
        db_bytes = db_size_bytes(conn)
        errors = conn.execute(
            "select name, error from files where owner = %s and status = 'erro' order by name", (owner,)
        ).fetchall()

    print("\n=== Relatório ===")
    if stop_reason:
        print(f"PARCIAL: parou por {stop_reason}")
    print(f"Duração:            {time.time() - t0:.0f}s")
    print(f"Listados:           {listed}")
    print(f"Ignorados:          {sum(ignored.values())} (formato não suportado)")
    for mime, c in ignored.most_common(8):
        print(f"                      {c:5d}  {mime}")
    print(f"Suportados:         {supported}")
    print(f"  pulados (sem mudança): {skipped}")
    print(f"  processados:           {processed}  {dict(statuses)}")
    print(f"  removidos do índice:   {removed}")
    print(f"No índice:          {n_files} arquivos")
    print(f"Tabela files:       {files_bytes / 1024:.0f} KB (média {files_bytes / max(1, n_files) / 1024:.1f} KB por arquivo, com índices)")
    print(f"Banco inteiro:      {db_bytes / (1024 * 1024):.1f} MB de 500 MB")
    if errors:
        print(f"Com erro ({len(errors)}):")
        for name, err in errors:
            print(f"  - {name}: {err}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
