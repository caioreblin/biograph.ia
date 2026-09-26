"""Metadados a partir da listagem do Drive: tipo, datas, GPS, câmera e nome normalizado.

Não baixa nada: EXIF de fotos vem de imageMediaMetadata, que a própria API devolve.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Literal

from .drive import DriveItem

Kind = Literal["jpg", "png", "pdf", "docx", "txt", "gdoc"]
DateSource = Literal["exif", "documento", "drive"]

_BY_MIME: dict[str, Kind] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "application/vnd.google-apps.document": "gdoc",
}
# Uploads com mimeType genérico (application/octet-stream) caem na extensão.
_BY_EXT: dict[str, Kind] = {
    ".jpg": "jpg", ".jpeg": "jpg", ".png": "png", ".pdf": "pdf", ".docx": "docx", ".txt": "txt",
}

# EXIF não tem fuso; o acervo é brasileiro. Offset fixo evita depender do tzdata no Windows.
_EXIF_TZ = timezone(timedelta(hours=-3))
_MIN_PLAUSIBLE = datetime(1990, 1, 1, tzinfo=timezone.utc)


@dataclass
class FileMeta:
    drive_file_id: str
    name: str
    name_search: str
    path: str
    mime_type: str
    kind: Kind
    size: int | None
    web_view_link: str
    drive_created_at: datetime
    drive_modified_at: datetime
    captured_at: datetime | None = None
    lat: float | None = None
    lon: float | None = None
    camera: str | None = None
    metadata: dict = field(default_factory=dict)


def classify(mime_type: str, name: str) -> Kind | None:
    """Tipo suportado, ou None para ignorar (vídeo, planilha, zip, atalho...)."""
    if mime_type in _BY_MIME:
        return _BY_MIME[mime_type]
    if mime_type == "application/octet-stream":
        return _BY_EXT.get(PurePosixPath(name).suffix.lower())
    return None


def normalize_name(name: str) -> str:
    """Quebra o nome em palavras, mantendo as originais e acrescentando as partes.

    'IMG-20260113-WA0134.jpg' -> 'IMG 20260113 WA0134 jpg WA 0134'
    'WhatsApp Image.jpeg'     -> 'WhatsApp Image jpeg Whats App'
    """
    base = re.sub(r"[_\-.+()\[\]{},;]+", " ", name).split()
    split = " ".join(base)
    split = re.sub(r"(?<=[a-zà-ÿ])(?=[A-ZÀ-Þ])", " ", split)  # camelCase
    split = re.sub(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", split)  # letra|dígito
    extra = [t for t in dict.fromkeys(split.split()) if t not in base]
    return " ".join(base + extra)


def parse_rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_exif_time(value: str | None) -> datetime | None:
    """'2019:12:07 18:50:25' -> datetime em UTC-3. Datas zeradas ou inválidas viram None."""
    if not value:
        return None
    try:
        dt = datetime.strptime(value.strip()[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return dt.replace(tzinfo=_EXIF_TZ)


def _plausible(dt: datetime | None) -> bool:
    return dt is not None and _MIN_PLAUSIBLE <= dt <= datetime.now(timezone.utc) + timedelta(days=1)


def _camera(make: str | None, model: str | None) -> str | None:
    make, model = (make or "").strip(), (model or "").strip()
    if model.lower().startswith(make.lower()):
        make = ""
    return " ".join(p for p in (make, model) if p) or None


def from_drive_item(item: DriveItem) -> FileMeta | None:
    """Metadados do arquivo, ou None se o tipo não é suportado."""
    kind = classify(item.mime_type, item.name)
    if kind is None:
        return None

    meta = FileMeta(
        drive_file_id=item.id,
        name=item.name,
        name_search=normalize_name(item.name),
        path=item.path,
        mime_type=item.mime_type,
        kind=kind,
        size=item.size,
        web_view_link=item.web_view_link,
        drive_created_at=parse_rfc3339(item.created_time),
        drive_modified_at=parse_rfc3339(item.modified_time),
    )

    im = item.image_meta
    if im:
        captured = parse_exif_time(im.get("time"))
        meta.captured_at = captured if _plausible(captured) else None
        loc = im.get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat is not None and lon is not None and (lat, lon) != (0, 0):
            meta.lat, meta.lon = float(lat), float(lon)
        meta.camera = _camera(im.get("cameraMake"), im.get("cameraModel"))
        meta.metadata = {
            k: v
            for k, v in {"camera": meta.camera, "lat": meta.lat, "lon": meta.lon,
                         "altitude": loc.get("altitude")}.items()
            if v is not None
        }
    return meta


def effective_date(
    captured_at: datetime | None,
    doc_created_at: datetime | None,
    drive_created_at: datetime,
    drive_modified_at: datetime,
) -> tuple[datetime, DateSource]:
    """Data usada no filtro de ano: EXIF > metadado interno do documento > Drive.

    No Drive usa a menor entre criação e modificação: uploads preservam a data original
    do arquivo em modifiedTime, enquanto createdTime é a data do envio.
    """
    if _plausible(captured_at):
        return captured_at, "exif"
    if _plausible(doc_created_at):
        return doc_created_at, "documento"
    return min(drive_created_at, drive_modified_at), "drive"
