"""Monta o texto de metadados (peso C do search_vector)."""

from datetime import datetime, timedelta, timezone

from .geocode import Place
from .metadata import FileMeta

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
_LOCAL_TZ = timezone(timedelta(hours=-3))


def build_search_meta(meta: FileMeta, place: Place | None, date: datetime) -> str:
    """'Schroeder Santa Catarina SC samsung SM-A750G dezembro 2019'."""
    local = date.astimezone(_LOCAL_TZ)
    parts = [
        place and place.city,
        place and place.state,
        place and place.state_code,
        meta.camera,
        MONTHS_PT[local.month - 1],
        str(local.year),
    ]
    return " ".join(p for p in parts if p)
