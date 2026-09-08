# backend/core/upload_validator.py
import os
import uuid
import tempfile
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from backend.core.config import settings


def generate_safe_temp_path(extension: str) -> str:
    """
    Generate an unguessable randomized temporary file path in the OS temp directory.
    Never uses user-supplied filenames to prevent path traversal or collision.
    """
    if extension and not extension.startswith("."):
        clean_ext = f".{extension.lower()}"
    elif extension:
        clean_ext = extension.lower()
    else:
        clean_ext = ".tmp"
    unique_filename = f"mediscan_{uuid.uuid4().hex}{clean_ext}"
    return os.path.join(tempfile.gettempdir(), unique_filename)


def validate_text_length(text: Optional[str]) -> None:
    """
    Validate that user symptom text does not exceed the configured length limit.
    """
    if text and len(text) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symptom text exceeds maximum allowed limit of {settings.MAX_TEXT_LENGTH} characters."
        )


def validate_image_file(file: UploadFile) -> None:
    """
    Validate an uploaded medicine image against allowed extensions, size,
    MIME type, and binary magic bytes.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file or filename is missing."
        )

    # 1. Extension check
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # 2. Read initial chunk for size and magic byte inspection
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > settings.MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image file size ({size / (1024*1024):.1f}MB) exceeds maximum limit of {settings.MAX_IMAGE_SIZE_BYTES / (1024*1024):.0f}MB."
        )

    if size < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty or corrupted."
        )

    header = file.file.read(32)
    file.file.seek(0)

    # 3. Magic Byte Verification
    is_valid = False
    if header.startswith(b"\xff\xd8\xff"):  # JPEG
        is_valid = True
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
        is_valid = True
    elif len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":  # WebP
        is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file signature. File content does not match expected image format."
        )


def validate_audio_file(file: UploadFile) -> None:
    """
    Validate an uploaded voice audio clip against allowed extensions, size,
    and binary magic bytes.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file or filename is missing."
        )

    # 1. Extension check
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_AUDIO_EXTENSIONS)}"
        )

    # 2. Size check
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > settings.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file size ({size / (1024*1024):.1f}MB) exceeds maximum limit of {settings.MAX_AUDIO_SIZE_BYTES / (1024*1024):.0f}MB."
        )

    if size < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty or corrupted."
        )

    header = file.file.read(32)
    file.file.seek(0)

    # 3. Binary Magic Byte Verification
    is_valid = False
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE":  # WAV
        is_valid = True
    elif header.startswith(b"ID3") or (len(header) >= 2 and header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa")):  # MP3
        is_valid = True
    elif header.startswith(b"\x1a\x45\xdf\xa3"):  # WebM / EBML / Matroska
        is_valid = True
    elif header.startswith(b"OggS"):  # OGG
        is_valid = True
    elif len(header) >= 8 and header[4:8] == b"ftyp":  # M4A / MP4
        is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio file signature. File content does not match expected audio format."
        )
