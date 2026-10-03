"""Conexão com o Postgres (Supabase), isolada para trocar de driver sem tocar no resto.

Usa pg8000 (Python puro) porque o Smart App Control do Windows bloqueia a DLL do
psycopg-binary na máquina do dev. No worker da Etapa 3, que roda em Linux, dá para
voltar ao psycopg trocando só este arquivo.
"""

import json
import ssl
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.dbapi as _dbapi

_dbapi.paramstyle = "pyformat"  # aceita %s e %(nome)s

Error = _dbapi.Error


class Connection:
    """Conexão em autocommit com execute() que devolve o cursor (fetchone/fetchall/rowcount)."""

    def __init__(self, raw: _dbapi.Connection):
        self._raw = raw

    def execute(self, sql: str, params: tuple | dict | None = None):
        cur = self._raw.cursor()
        cur.execute(sql, params if params is not None else ())
        return cur

    def close(self) -> None:
        self._raw.close()

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _ssl_context(ca_cert: Path | None) -> ssl.SSLContext:
    if ca_cert and ca_cert.exists():
        return ssl.create_default_context(cafile=str(ca_cert))
    # Sem o certificado da CA do Supabase: criptografa sem verificar o servidor,
    # o mesmo que o sslmode=prefer padrão do libpq.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def connect(url: str, ca_cert: Path | None = None) -> Connection:
    """Conecta a partir de uma URL postgresql://usuario:senha@host:porta/banco."""
    u = urlparse(url)
    raw = _dbapi.connect(
        user=unquote(u.username or ""),
        password=unquote(u.password or ""),
        host=u.hostname,
        port=u.port or 5432,
        database=u.path.lstrip("/") or "postgres",
        ssl_context=_ssl_context(ca_cert),
        timeout=30,
    )
    raw.autocommit = True
    return Connection(raw)


def jsonb(value) -> str:
    """Serializa para um parâmetro que a query converte com ::jsonb."""
    return json.dumps(value, ensure_ascii=False, default=str)
