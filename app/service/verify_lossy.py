import os
import tempfile
import jpeglib
from core.lossy.global_hash.utils import *


def read_dct_from_bytes(file_bytes: bytes):
    temp_input = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(file_bytes)
            temp_input = f.name

        return jpeglib.read_dct(temp_input)

    finally:
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)


def verify_service_bytes(file_bytes: bytes, secret_key: str):
    jpeg = read_dct_from_bytes(file_bytes)

    Y = jpeg.Y
    Cb = jpeg.Cb if getattr(jpeg, "Cb", None) is not None else None
    Cr = jpeg.Cr if getattr(jpeg, "Cr", None) is not None else None

    positions = collect_embed_positions(
        Y, secret_key, HASH_BITS, MIN_ABS_COEFF
    )

    if len(positions) < HASH_BITS:
        return {"is_valid": False, "reason": "Không đủ vị trí"}

    embedded = extract_bits_from_positions(Y, positions)

    recomputed = compute_global_hash_bits(
        Y, Cb, Cr, secret_key, positions, HASH_BITS
    )

    bit_errors = sum(a != b for a, b in zip(embedded, recomputed))

    return {
        "is_valid": bit_errors == 0,
        "bit_errors": bit_errors,
        "embedded_hash": bits_to_bytes(embedded).hex(),
        "recomputed_hash": bits_to_bytes(recomputed).hex(),
    }