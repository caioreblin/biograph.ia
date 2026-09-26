"""Acesso ao Google Drive: autenticação, listagem recursiva, download e export."""

import io
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
ROOT_NAME = "Meu Drive"
RETRIES = 5  # backoff exponencial do próprio cliente Google (403 de cota, 429, 5xx)

_FILE_FIELDS = (
    "id, name, mimeType, size, createdTime, modifiedTime, webViewLink, "
    "imageMediaMetadata(time, location, cameraMake, cameraModel)"
)


class AuthError(Exception):
    """Token expirado ou revogado; exige nova autorização no navegador."""


class ExportTooLarge(Exception):
    """O Drive recusa exportar Google Docs acima de 10 MB."""


@dataclass(frozen=True)
class DriveItem:
    id: str
    name: str
    mime_type: str
    path: str  # caminho da pasta que contém o arquivo: "Meu Drive/EMPRESA"
    web_view_link: str
    size: int | None  # None para arquivos nativos do Google (Docs etc.)
    created_time: str  # RFC 3339
    modified_time: str  # RFC 3339
    image_meta: dict = field(default_factory=dict)


def get_service(credentials_path: Path, token_path: Path) -> Resource:
    """Autentica (reaproveitando o token salvo) e devolve o cliente da Drive API v3."""
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        pass
    elif creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            raise AuthError(
                "Token do Google expirado ou revogado (em modo de teste ele expira em 7 dias). "
                f"Apague {token_path} e rode de novo para autorizar."
            ) from e
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_owner_email(svc: Resource) -> str:
    about = svc.about().get(fields="user(emailAddress)").execute(num_retries=RETRIES)
    return about["user"]["emailAddress"]


def _root_path(svc: Resource, root_id: str) -> str:
    if root_id == "root":
        return ROOT_NAME
    meta = svc.files().get(fileId=root_id, fields="name").execute(num_retries=RETRIES)
    return meta["name"]


def _children(svc: Resource, folder_id: str) -> Iterator[dict]:
    page_token = None
    while True:
        resp = (
            svc.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields=f"nextPageToken, files({_FILE_FIELDS})",
                pageSize=1000,
                pageToken=page_token,
            )
            .execute(num_retries=RETRIES)
        )
        yield from resp.get("files", [])
        page_token = resp.get("nextPageToken")
        if not page_token:
            return


def list_tree(svc: Resource, root_id: str = "root") -> Iterator[DriveItem]:
    """Percorre a pasta raiz em largura e devolve todo arquivo (não pasta) fora da lixeira."""
    queue = deque([(root_id, _root_path(svc, root_id))])
    seen = {root_id}
    while queue:
        folder_id, path = queue.popleft()
        for f in _children(svc, folder_id):
            if f["mimeType"] == FOLDER_MIME:
                if f["id"] not in seen:
                    seen.add(f["id"])
                    queue.append((f["id"], f"{path}/{f['name']}"))
                continue
            yield DriveItem(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                path=path,
                web_view_link=f.get("webViewLink", ""),
                size=int(f["size"]) if "size" in f else None,
                created_time=f["createdTime"],
                modified_time=f["modifiedTime"],
                image_meta=f.get("imageMediaMetadata", {}),
            )


def download(svc: Resource, file_id: str, max_bytes: int, size: int | None = None) -> bytes | None:
    """Baixa o binário. Devolve None se o arquivo passar de max_bytes."""
    if size is not None and size > max_bytes:
        return None
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, svc.files().get_media(fileId=file_id))
    done = False
    while not done:
        _, done = downloader.next_chunk(num_retries=RETRIES)
        if buf.tell() > max_bytes:
            return None
    return buf.getvalue()


def export_gdoc_text(svc: Resource, file_id: str) -> str:
    """Exporta um Google Docs como texto puro."""
    try:
        data = svc.files().export(fileId=file_id, mimeType="text/plain").execute(num_retries=RETRIES)
    except HttpError as e:
        if "exportSizeLimitExceeded" in str(e.content):
            raise ExportTooLarge(file_id) from e
        raise
    return data.decode("utf-8-sig", errors="replace")
