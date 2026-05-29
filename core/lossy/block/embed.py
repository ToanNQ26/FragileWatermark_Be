from .utils_block import (
    get_watermark_positions, get_data_coefficients,
    calculate_crc_checksum, int_to_binary,
    force_parity_stable, DEFAULT_KEY,
    MIN_ABS_COEFF, WATERMARK_BITS
)


def embed_watermark(jpeg, secret_key: str = DEFAULT_KEY):
    Y = jpeg.Y.copy()
    h_blocks, w_blocks = Y.shape[:2]

    for by in range(h_blocks):
        for bx in range(w_blocks):
            block = Y[by, bx]
            block_idx = by * w_blocks + bx

            positions = get_watermark_positions(secret_key, by, bx)

            data_coeffs = get_data_coefficients(block, positions)

            checksum = calculate_crc_checksum(data_coeffs, secret_key, block_idx)

            bits = int_to_binary(checksum)

            for i, (u, v) in enumerate(positions):
                Y[by, bx, u, v] = force_parity_stable(
                    Y[by, bx, u, v], int(bits[i]), MIN_ABS_COEFF
                )

    jpeg.Y = Y
    return jpeg