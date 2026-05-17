from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from io import BytesIO
import base64
from PIL import Image

from core.lossless.embed import embed_watermark

router = APIRouter(prefix="/api")


@router.post("/embed")
async def embed(file: UploadFile = File(...), key: str = Form("")):
    image_bytes = await file.read()

    image = Image.open(BytesIO(image_bytes))

    watermarked_image, image_info = embed_watermark(image, key)

    buffer = BytesIO()
    watermarked_image.save(buffer, format="PNG")

    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return JSONResponse({
        "image_base64": f"data:image/png;base64,{image_base64}",
        "info": image_info
    })