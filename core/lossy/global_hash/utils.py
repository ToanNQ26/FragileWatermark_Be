import hashlib
import numpy as np
import base64
from io import BytesIO
import os
import tempfile
import jpeglib

# =========================
# CONFIG
# =========================

CANDIDATES = [
    (0, 3), (0, 4),
    (1, 2), (1, 3), (1, 4), (1, 5),
    (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6),
    (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5),
    (4, 0), (4, 1), (4, 2), (4, 3), (4, 4),
    (5, 1),
]

HASH_BITS = 128
MIN_ABS_COEFF = 2


# =========================
# BASIC UTILS
# =========================

def int16_bytes(arr: np.ndarray) -> bytes:
    return np.asarray(arr, dtype=np.int16).tobytes()


def bits_to_bytes(bits):
    out = bytearray()
    for i in range(0, len(bits), 8):
        b = 0
        for bit in bits[i:i + 8]:
            b = (b << 1) | int(bit)
        out.append(b)
    return bytes(out)


def bytes_to_bits(data: bytes, n_bits: int):
    bits = []
    for byte in data:
        for k in range(7, -1, -1):
            bits.append((byte >> k) & 1)
            if len(bits) == n_bits:
                return bits
    return bits


# =========================
# RANDOM POSITION
# =========================

def get_block_seed(secret_key: str, by: int, bx: int) -> int:
    payload = f"{secret_key}|{by}|{bx}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


def get_shuffled_candidates(secret_key, by, bx):
    seed = get_block_seed(secret_key, by, bx)
    rng = np.random.default_rng(seed)

    idx = np.arange(len(CANDIDATES))
    rng.shuffle(idx)

    return [CANDIDATES[i] for i in idx]


# =========================
# EMBED POSITION
# =========================

def collect_embed_positions(Y, secret_key, required_bits, min_abs):
    positions = []
    used = set()

    h_blocks, w_blocks = Y.shape[:2]

    for by in range(h_blocks):
        for bx in range(w_blocks):
            block = Y[by, bx]
            shuffled = get_shuffled_candidates(secret_key, by, bx)

            for (u, v) in shuffled:
                pos = (by, bx, u, v)

                if pos in used:
                    continue

                if abs(int(block[u, v])) >= min_abs:
                    positions.append(pos)
                    used.add(pos)

                    if len(positions) == required_bits:
                        return positions

    return positions


# =========================
# HASH
# =========================

def compute_global_hash_bits(Y, Cb, Cr, secret_key, embed_positions, n_bits):
    embed_map = {}
    for by, bx, u, v in embed_positions:
        embed_map.setdefault((by, bx), set()).add((u, v))

    feats = []

    # Y
    for by in range(Y.shape[0]):
        for bx in range(Y.shape[1]):
            block = Y[by, bx]
            exclude = embed_map.get((by, bx), set())

            for i in range(8):
                for j in range(8):
                    if (i, j) == (0, 0) or (i, j) in exclude:
                        continue
                    feats.append(int(block[i, j]))

    # Cb/Cr
    if Cb is not None and Cr is not None:
        for by in range(Cb.shape[0]):
            for bx in range(Cb.shape[1]):
                for i in range(8):
                    for j in range(8):
                        if (i, j) != (0, 0):
                            feats.append(int(Cb[by, bx, i, j]))
                            feats.append(int(Cr[by, bx, i, j]))

    payload = int16_bytes(np.array(feats)) + secret_key.encode()
    digest = hashlib.sha256(payload).digest()

    return bytes_to_bits(digest, n_bits)


# =========================
# EMBED / EXTRACT
# =========================

def force_parity_stable(value, target_bit, min_abs):
    v = int(value)

    if v != 0 and abs(v) % 2 == target_bit and abs(v) >= min_abs:
        return v

    for delta in [1, -1, 2, -2, 3, -3]:
        c = v + delta
        if c != 0 and abs(c) % 2 == target_bit and abs(c) >= min_abs:
            return c

    return min_abs + (min_abs % 2 != target_bit)


def extract_bits_from_positions(Y, positions):
    return [abs(int(Y[by, bx, u, v])) % 2 for (by, bx, u, v) in positions]

# ========================
# Helpers base64
# ========================
def file_to_bytes(upload_file):
    return upload_file.file.read()


def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def base64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(b64)

# read anh write bas64
def read_dct_from_bytes(file_bytes: bytes):
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(file_bytes)
            temp_path = f.name

        return jpeglib.read_dct(temp_path)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def write_dct_to_base64(jpeg) -> str:
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            temp_path = f.name

        jpeg.write_dct(temp_path)

        with open(temp_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)