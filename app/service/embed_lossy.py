import jpeglib
from core.lossy.global_hash.utils import *
import tempfile
import os


def embed_service_bytes(file_bytes: bytes, secret_key: str):
    # đọc JPEG từ memory
    jpeg = read_dct_from_bytes(file_bytes)

    Y = jpeg.Y.copy()
    Cb = jpeg.Cb.copy() if getattr(jpeg, "Cb", None) is not None else None
    Cr = jpeg.Cr.copy() if getattr(jpeg, "Cr", None) is not None else None

    positions = collect_embed_positions(
        Y, secret_key, HASH_BITS, MIN_ABS_COEFF
    )

    if len(positions) < HASH_BITS:
        raise ValueError("Không đủ vị trí nhúng")

    hash_bits = compute_global_hash_bits(
        Y, Cb, Cr, secret_key, positions, HASH_BITS
    )

    for bit, (by, bx, u, v) in zip(hash_bits, positions):
        Y[by, bx, u, v] = force_parity_stable(
            Y[by, bx, u, v], bit, MIN_ABS_COEFF
        )

    jpeg.Y = Y

    temp_output = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        ) as f:
            temp_output = f.name

        # print("Temp file:", temp_output)
        jpeg.write_dct(temp_output)

        with open(temp_output, "rb") as f:
            output_bytes = f.read()

        return {
            "image_base64": bytes_to_base64(output_bytes)
        }

    finally:
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)


