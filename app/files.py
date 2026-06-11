import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}

IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
DOCUMENT_CONTENT_TYPES = {"application/pdf"}


def get_upload_root() -> Path:
    root = Path(get_settings().UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_upload_dirs() -> None:
    root = get_upload_root()
    (root / "images").mkdir(parents=True, exist_ok=True)
    (root / "documents").mkdir(parents=True, exist_ok=True)


def _validate_extension(filename: str, allowed: set[str]) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {allowed_list}",
        )
    return ext


async def save_image(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл не выбран")

    ext = _validate_extension(file.filename, ALLOWED_IMAGE_EXTENSIONS)
    if file.content_type and file.content_type not in IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый формат изображения")

    return await _save_file(file, "images", ext)


async def save_document(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл не выбран")

    ext = _validate_extension(file.filename, ALLOWED_DOCUMENT_EXTENSIONS)
    if file.content_type and file.content_type not in DOCUMENT_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Допустим только PDF")

    return await _save_file(file, "documents", ext)


async def _save_file(file: UploadFile, subdir: str, ext: str) -> str:
    ensure_upload_dirs()
    filename = f"{uuid.uuid4().hex}{ext}"
    destination = get_upload_root() / subdir / filename

    content = await file.read()
    max_size = get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой (макс. {get_settings().MAX_UPLOAD_SIZE_MB} МБ)",
        )

    destination.write_bytes(content)
    return f"/uploads/{subdir}/{filename}"


async def resolve_image_url(
    uploaded_file: UploadFile | None,
    manual_url: str,
) -> str | None:
    if uploaded_file and uploaded_file.filename:
        return await save_image(uploaded_file)
    cleaned = manual_url.strip()
    return cleaned or None


async def resolve_document_url(
    uploaded_file: UploadFile | None,
    manual_url: str,
) -> str | None:
    if uploaded_file and uploaded_file.filename:
        return await save_document(uploaded_file)
    cleaned = manual_url.strip()
    return cleaned or None
