"""GPS -> cidade e estado, pelo Nominatim (OpenStreetMap), com cache no banco.

Política de uso do Nominatim: no máximo 1 requisição por segundo e User-Agent que
identifique o app com um contato. O cache por coordenada arredondada (2 casas, ~1 km)
faz fotos do mesmo lugar custarem uma consulta só.
"""

import time
from dataclasses import dataclass
from decimal import Decimal

import psycopg
import requests
from psycopg.types.json import Jsonb

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
MIN_INTERVAL_S = 1.1  # folga sobre o limite de 1 req/s
TIMEOUT_S = 10

_last_request = 0.0


@dataclass(frozen=True)
class Place:
    city: str | None
    state: str | None  # nome completo: "Santa Catarina"
    state_code: str | None  # sigla: "SC"


def _round(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _place_from_raw(raw: dict | None) -> Place | None:
    address = (raw or {}).get("address") or {}
    city = next(
        (address[k] for k in ("city", "town", "village", "municipality", "suburb") if address.get(k)),
        None,
    )
    if city is None and not address.get("state"):
        return None
    iso = address.get("ISO3166-2-lvl4", "")
    return Place(city=city, state=address.get("state"), state_code=iso.split("-")[-1] if "-" in iso else None)


def _throttle() -> None:
    global _last_request
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _fetch(lat: Decimal, lon: Decimal, contact_email: str) -> dict | None:
    """Consulta o Nominatim. None = falha temporária (não deve ir para o cache)."""
    _throttle()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"format": "jsonv2", "lat": str(lat), "lon": str(lon), "zoom": 10,
                    "addressdetails": 1, "accept-language": "pt-BR"},
            headers={"User-Agent": f"biographai-poc/0.1 ({contact_email})"},
            timeout=TIMEOUT_S,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:  # 429, 5xx: tenta de novo na próxima indexação
        return None
    return resp.json()  # {"error": "Unable to geocode"} no mar etc. também é cacheado


def reverse(conn: psycopg.Connection, lat: float, lon: float, contact_email: str) -> Place | None:
    """Cidade e estado da coordenada: cache primeiro, depois Nominatim.

    Grava no cache sem dar commit; use uma conexão em autocommit ou faça o commit.
    """
    lat_r, lon_r = _round(lat), _round(lon)
    row = conn.execute(
        "select raw from geocode_cache where lat_r = %s and lon_r = %s", (lat_r, lon_r)
    ).fetchone()
    if row is not None:
        return _place_from_raw(row[0])

    raw = _fetch(lat_r, lon_r, contact_email)
    if raw is None:
        return None
    place = _place_from_raw(raw)
    conn.execute(
        """insert into geocode_cache (lat_r, lon_r, city, state, raw)
           values (%s, %s, %s, %s, %s) on conflict do nothing""",
        (lat_r, lon_r, place and place.city, place and place.state, Jsonb(raw)),
    )
    return place
