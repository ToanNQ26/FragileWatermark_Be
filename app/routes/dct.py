from fastapi import APIRouter, UploadFile, File, Form
from app.service.embed_lossy import embed_service_bytes
from app.service.verify_lossy import verify_service_bytes

router = APIRouter()


# =========================
# EMBED
# =========================
@router.post("/embed-dct")
async def embed_dct(
    file: UploadFile = File(...),
    key: str = Form(...)
):
    file_bytes = await file.read()

    result = embed_service_bytes(
        file_bytes=file_bytes,
        secret_key=key
    )

    return result


# =========================
# VERIFY
# =========================
@router.post("/verify-dct")
async def verify_dct(
    file: UploadFile = File(...),
    key: str = Form(...)
):
    file_bytes = await file.read()

    result = verify_service_bytes(
        file_bytes=file_bytes,
        secret_key=key
    )

    return result