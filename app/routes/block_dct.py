from fastapi import APIRouter, UploadFile, File, Form
from app.service.block import embed_service_bytes, verify_service_bytes, tamper_service_bytes

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
# TAMPER (DCT domain)
# =========================
@router.post("/tamper-dct")
async def tamper_dct(
    file: UploadFile = File(...),
    region: str = Form("center")
):
    file_bytes = await file.read()

    result = tamper_service_bytes(
        file_bytes=file_bytes,
        region=region
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