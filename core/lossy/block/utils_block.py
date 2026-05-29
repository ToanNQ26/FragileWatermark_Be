import hashlib
import numpy as np

CANDIDATES = [
    (0, 3), (0, 4),
    (1, 2), (1, 3), (1, 4), (1, 5),
    (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6),
    (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5),
    (4, 0), (4, 1), (4, 2), (4, 3), (4, 4),
    (5, 1),
]

MIN_ABS_COEFF = 2
WATERMARK_BITS = 8
DEFAULT_KEY = "default_fragile_key"

CRC8_POLYNOMIAL = 0x07


def crc8(data: bytes, polynomial: int = CRC8_POLYNOMIAL) -> int:
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


def calculate_crc_checksum(data_coeffs: np.ndarray, secret_key: str = "", block_index: int = 0) -> int:
    data_bytes = data_coeffs.astype(np.int16).tobytes()
    key_bytes = secret_key.encode('utf-8') if secret_key else b''
    block_idx_bytes = block_index.to_bytes(4, 'little')
    return crc8(key_bytes + block_idx_bytes + data_bytes)


def get_block_seed(secret_key: str, by: int, bx: int) -> int:
    payload = f"{secret_key}|{by}|{bx}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


def get_watermark_positions(secret_key: str, by: int, bx: int) -> list:
    seed = get_block_seed(secret_key, by, bx)
    rng = np.random.default_rng(seed)
    idx = np.arange(len(CANDIDATES))
    rng.shuffle(idx)
    return [CANDIDATES[i] for i in idx[:WATERMARK_BITS]]


def get_data_coefficients(block: np.ndarray, watermark_positions: list) -> np.ndarray:
    mask = np.ones(64, dtype=bool)
    mask[0] = False
    for u, v in watermark_positions:
        mask[u * 8 + v] = False
    return block.flatten()[mask]


def get_watermark_coefficients(block: np.ndarray, watermark_positions: list) -> np.ndarray:
    return np.array([int(block[u, v]) for u, v in watermark_positions], dtype=np.int16)


def force_parity_stable(value, target_bit, min_abs):
    v = int(value)
    if v != 0 and abs(v) % 2 == target_bit and abs(v) >= min_abs:
        return v
    for delta in [1, -1, 2, -2, 3, -3]:
        c = v + delta
        if c != 0 and abs(c) % 2 == target_bit and abs(c) >= min_abs:
            return c
    return min_abs + (min_abs % 2 != target_bit)


def extract_bits(coefficients: np.ndarray) -> np.ndarray:
    return np.array([abs(int(c)) % 2 for c in coefficients], dtype=np.uint8)


def int_to_binary(n: int) -> np.ndarray:
    return np.array([int(b) for b in format(n, '08b')], dtype=np.uint8)


def binary_to_int(bits: np.ndarray) -> int:
    return int(''.join(str(b) for b in bits), 2)


def create_tamper_mask(blocks_shape: tuple, tampered_blocks: list) -> np.ndarray:
    mask = np.zeros((blocks_shape[0] * 8, blocks_shape[1] * 8), dtype=np.uint8)
    for row, col in tampered_blocks:
        mask[row*8:(row+1)*8, col*8:(col+1)*8] = 255
    return mask


def overlay_mask_on_image(image: np.ndarray, mask: np.ndarray,tampered_color=(255, 0, 0)) -> np.ndarray:
    is_grayscale = len(image.shape) == 2
    has_alpha = len(image.shape) == 3 and image.shape[2] == 4

    if is_grayscale:
        rgb_img = np.stack([image, image, image], axis=-1)
    elif has_alpha:
        rgb_img = image[:, :, :3].copy()
    else:
        rgb_img = image.copy()

    tampered = mask > 0
    for i, color_val in enumerate(tampered_color):
        rgb_img[:, :, i] = np.where(tampered, color_val, rgb_img[:, :, i])

    return rgb_img.astype(np.uint8)


def read_dct_from_bytes(file_bytes: bytes):
    import tempfile
    import os
    import jpeglib
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(file_bytes)
            temp_path = f.name
        return jpeglib.read_dct(temp_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def write_dct_to_bytes(jpeg) -> bytes:
    import tempfile
    import os
    import jpeglib
    temp_output = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            temp_output = f.name
        jpeg.write_dct(temp_output)
        with open(temp_output, "rb") as f:
            return f.read()
    finally:
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)


def bytes_to_base64(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("utf-8")


def base64_to_bytes(b64: str) -> bytes:
    import base64
    return base64.b64decode(b64)