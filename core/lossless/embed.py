from PIL import Image
import numpy as np

from .utils import (
    extract_blue_channel, merge_blue_channel,
    calculate_crc_checksum, int_to_binary, embed_bit,
    DEFAULT_KEY, get_watermark_positions,
    get_data_pixels_for_block
)


def pil_to_array(image: Image.Image) -> tuple[np.ndarray, str]:
    if image.mode == "P":
        if "transparency" in image.info:
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
    elif image.mode not in ("L", "RGB", "RGBA"):
        if "A" in image.mode:
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

    mode = image.mode
    return np.array(image, dtype=np.uint8), mode


def array_to_pil(img_array: np.ndarray, mode: str) -> Image.Image:
    return Image.fromarray(img_array.astype(np.uint8), mode=mode)


def embed_watermark(image: Image.Image, secret_key: str = DEFAULT_KEY):
    img_array, mode = pil_to_array(image)

    orig_height, orig_width = img_array.shape[:2]

    print(f"Đã đọc ảnh: {orig_width}x{orig_height} (mode: {mode})")
    print(f"Secret key: {secret_key}")

    blue_channel = extract_blue_channel(img_array, mode)

    pad_h = (8 - orig_height % 8) % 8
    pad_w = (8 - orig_width % 8) % 8

    if pad_h > 0 or pad_w > 0:
        if mode == "L":
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode="edge")
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w)), mode="edge")
        else:
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode="edge")
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")

        print(f"Ảnh sau padding: {blue_channel.shape[1]}x{blue_channel.shape[0]}")

    height, width = blue_channel.shape
    watermarked_blue = blue_channel.copy()

    num_blocks_y = height // 8
    num_blocks_x = width // 8
    num_blocks = num_blocks_y * num_blocks_x

    print(f"Tổng số blocks: {num_blocks_x}x{num_blocks_y} = {num_blocks}")

    for block_row in range(num_blocks_y):
        for block_col in range(num_blocks_x):
            r_start = block_row * 8
            c_start = block_col * 8

            block_idx = block_row * num_blocks_x + block_col

            watermark_positions = get_watermark_positions(block_idx, secret_key)

            data_pixels = get_data_pixels_for_block(
                img_array,
                mode,
                block_row,
                block_col,
                watermark_positions
            )

            checksum = calculate_crc_checksum(
                data_pixels,
                mode,
                secret_key,
                block_idx
            )

            watermark_bits = int_to_binary(checksum)

            for i, (row, col) in enumerate(watermark_positions):
                old_value = watermarked_blue[r_start + row, c_start + col]
                watermarked_blue[r_start + row, c_start + col] = embed_bit(
                    old_value,
                    watermark_bits[i]
                )

    watermarked_array = merge_blue_channel(img_array, mode, watermarked_blue)

    watermarked_image = array_to_pil(watermarked_array, mode)

    image_info = {
        "mode": mode,
        "original_size": (orig_height, orig_width),
        "padded_size": (height, width),
        "secret_key": secret_key,
        "num_blocks": num_blocks,
        "blocks_shape": (num_blocks_y, num_blocks_x),
    }

    return watermarked_image, image_info


# if __name__ == "__main__":
#     import sys

#     if len(sys.argv) > 1:
#         input_path = sys.argv[1]
#         output_path = sys.argv[2] if len(sys.argv) > 2 else "output/watermarked.png"

#         image = Image.open(input_path)

#         watermarked_image, image_info = embed_watermark(image)

#         watermarked_image.save(output_path, format="PNG")

#         print("Đã lưu ảnh:", output_path)
#         print(image_info)
#     else:
#         print("Cách dùng: python embed.py <input_image> [output_image]")