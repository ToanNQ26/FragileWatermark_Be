import numpy as np

from .utils_block import (
    get_watermark_positions, get_data_coefficients,
    get_watermark_coefficients,
    calculate_crc_checksum, extract_bits, binary_to_int,
    create_tamper_mask, overlay_mask_on_image,
    DEFAULT_KEY
)


def verify_watermark(jpeg, secret_key: str = DEFAULT_KEY):
    Y = jpeg.Y
    h_blocks, w_blocks = Y.shape[:2]
    tampered_blocks = []
    verified_blocks = []

    for by in range(h_blocks):
        for bx in range(w_blocks):
            block = Y[by, bx]
            block_idx = by * w_blocks + bx

            positions = get_watermark_positions(secret_key, by, bx)

            watermark_coeffs = get_watermark_coefficients(block, positions)
            extracted_bits = extract_bits(watermark_coeffs)
            extracted_checksum = binary_to_int(extracted_bits)

            data_coeffs = get_data_coefficients(block, positions)
            calculated_checksum = calculate_crc_checksum(data_coeffs, secret_key, block_idx)

            if extracted_checksum != calculated_checksum:
                tampered_blocks.append((by, bx))
            else:
                verified_blocks.append((by, bx))

    return {
        'tampered_blocks': tampered_blocks,
        'total_blocks': h_blocks * w_blocks,
        'tamper_count': len(tampered_blocks),
        'verified_count': len(verified_blocks),
        'blocks_shape': (h_blocks, w_blocks),
    }


def verify_and_generate_images(jpeg, pil_img_array: np.ndarray, mode: str, secret_key: str):
    result = verify_watermark(jpeg, secret_key)

    h_blocks, w_blocks = result['blocks_shape']
    mask_h = h_blocks * 8
    mask_w = w_blocks * 8

    tamper_mask = create_tamper_mask(
        result['blocks_shape'],
        result['tampered_blocks']
    )

    orig_h, orig_w = pil_img_array.shape[:2]
    out_h = min(mask_h, orig_h)
    out_w = min(mask_w, orig_w)

    tamper_mask = tamper_mask[:out_h, :out_w]

    overlay = overlay_mask_on_image(pil_img_array, tamper_mask)

    overlay = overlay[:orig_h, :orig_w, :]

    result['mask'] = tamper_mask
    result['overlay'] = overlay

    return result