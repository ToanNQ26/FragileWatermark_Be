import os
import tempfile
from io import BytesIO
from PIL import Image
import jpeglib
from core.lossy.block.verify import verify_and_generate_images
from core.lossy.block.embed import embed_watermark
from core.lossy.block.utils_block import read_dct_from_bytes, bytes_to_base64


def embed_service_bytes(file_bytes: bytes, secret_key: str):
    jpeg = read_dct_from_bytes(file_bytes)

    jpeg = embed_watermark(jpeg, secret_key)

    temp_output = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            temp_output = f.name

        jpeg.write_dct(temp_output)

        with open(temp_output, "rb") as f:
            output_bytes = f.read()

        return {
            "image_base64": bytes_to_base64(output_bytes)
        }

    finally:
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)


import numpy as np
from core.lossy.block.utils_block import read_dct_from_bytes, write_dct_to_bytes, bytes_to_base64


def _zero_ac_coeffs(block: np.ndarray):
    for i in range(8):
        for j in range(8):
            if (i, j) != (0, 0):
                block[i, j] = 0


def tamper_service_bytes(file_bytes: bytes, region: str):
    jpeg = read_dct_from_bytes(file_bytes)
    Y = jpeg.Y
    h_blocks, w_blocks = Y.shape[:2]

    if region == "all":
        r0, c0, r1, c1 = 0, 0, h_blocks - 1, w_blocks - 1
    elif region == "center":
        r0, c0 = h_blocks // 4, w_blocks // 4
        r1, c1 = 3 * h_blocks // 4, 3 * w_blocks // 4
    elif region == "top-left":
        r0, c0 = 0, 0
        r1, c1 = max(0, h_blocks // 2 - 1), max(0, w_blocks // 2 - 1)
    elif region == "top-right":
        r0, c0 = 0, w_blocks // 2
        r1, c1 = max(0, h_blocks // 2 - 1), w_blocks - 1
    elif region == "bottom-left":
        r0, c0 = h_blocks // 2, 0
        r1, c1 = h_blocks - 1, max(0, w_blocks // 2 - 1)
    elif region == "bottom-right":
        r0, c0 = h_blocks // 2, w_blocks // 2
        r1, c1 = h_blocks - 1, w_blocks - 1
    elif region == "random":
        rng = np.random.RandomState(42)
        for by in range(h_blocks):
            for bx in range(w_blocks):
                if rng.random() < 0.15:
                    _zero_ac_coeffs(Y[by, bx])
        jpeg.Y = Y
        output_bytes = write_dct_to_bytes(jpeg)
        return {"image_base64": bytes_to_base64(output_bytes)}
    else:
        for by in range(h_blocks):
            for bx in range(w_blocks):
                _zero_ac_coeffs(Y[by, bx])
        jpeg.Y = Y
        output_bytes = write_dct_to_bytes(jpeg)
        return {"image_base64": bytes_to_base64(output_bytes)}

    r0 = max(0, min(r0, h_blocks - 1))
    r1 = max(0, min(r1, h_blocks - 1))
    c0 = max(0, min(c0, w_blocks - 1))
    c1 = max(0, min(c1, w_blocks - 1))

    for by in range(r0, r1 + 1):
        for bx in range(c0, c1 + 1):
            _zero_ac_coeffs(Y[by, bx])

    jpeg.Y = Y
    output_bytes = write_dct_to_bytes(jpeg)
    return {"image_base64": bytes_to_base64(output_bytes)}








def image_to_base64(img_array: np.ndarray) -> str:
    import base64
    buffer = BytesIO()
    Image.fromarray(img_array).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def verify_service_bytes(file_bytes: bytes, secret_key: str):
    jpeg = read_dct_from_bytes(file_bytes)

    img = Image.open(BytesIO(file_bytes))
    if img.mode == 'P':
        if 'transparency' in img.info:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
    elif img.mode not in ('L', 'RGB', 'RGBA'):
        img = img.convert('RGBA' if 'A' in img.mode else 'RGB')

    img_array = np.array(img, dtype=np.uint8)
    mode = img.mode

    result = verify_and_generate_images(jpeg, img_array, mode, secret_key)

    mask_base64 = image_to_base64(result["mask"])
    overlay_base64 = image_to_base64(result["overlay"])

    return {
        "is_valid": result["tamper_count"] == 0,
        "tamper_count": result["tamper_count"],
        "total_blocks": result["total_blocks"],
        "verified_count": result["verified_count"],
        "mask_base64": mask_base64,
        "overlay_base64": overlay_base64,
    }