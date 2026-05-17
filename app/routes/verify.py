from fastapi import APIRouter, UploadFile, File, Form
import base64
from io import BytesIO
from PIL import Image
import numpy as np

from core.lossless.verify import verify_and_generate_images

router = APIRouter(prefix="/api")


def image_to_base64(img):
    buffer = BytesIO()

    if isinstance(img, Image.Image):
        img.save(buffer, format="PNG")
    else:
        Image.fromarray(img).save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()


@router.post("/verify")
async def verify(file: UploadFile = File(...), key: str = Form("")):
    # 🔥 đọc file vào RAM
    file_bytes = await file.read()

    # 🔥 load ảnh từ RAM
    img = Image.open(BytesIO(file_bytes))

    # xử lý mode giống utils của bạn
    if img.mode == 'P':
        if 'transparency' in img.info:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
    elif img.mode not in ('L', 'RGB', 'RGBA'):
        img = img.convert('RGBA' if 'A' in img.mode else 'RGB')

    img_array = np.array(img, dtype=np.uint8)
    mode = img.mode

    # 🔥 verify trực tiếp
    result = verify_and_generate_images(img_array, mode, key)

    # 🔥 convert base64
    mask_base64 = image_to_base64(result["mask"])
    overlay_base64 = image_to_base64(result["overlay"])

    return {
        "is_valid": result["tamper_count"] == 0,
        "tamper_count": result["tamper_count"],
        "total_blocks": result["total_blocks"],
        "verified_count": result["verified_count"],
        "overlay_base64": overlay_base64,
        "mask_base64": mask_base64
    }