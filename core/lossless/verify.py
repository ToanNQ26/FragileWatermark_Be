"""
Module xác minh watermark cho fragile watermarking theo block.
Hỗ trợ cả ảnh grayscale (L) và ảnh màu (RGB, RGBA).
Checksum cho ảnh màu tính từ R+G+B (và A nếu RGBA) để phát hiện thay đổi ở bất kỳ kênh nào.
Dùng CRC-8 thay vì simple sum % 256 để tăng độ tin cậy.
"""
import numpy as np
from PIL import Image
from .utils import (
    load_image_full, extract_blue_channel,
    calculate_crc_checksum, 
    binary_to_int, extract_bit,
    create_tamper_mask, overlay_mask_on_image,
    check_input_warning, DEFAULT_KEY, get_watermark_positions,
    get_data_pixels_for_block, get_watermark_pixels_from_block
)


def verify_watermark(watermarked_path: str, secret_key: str = DEFAULT_KEY) -> dict:
    """
    Xác minh tính toàn vẹn watermark của ảnh đã nhúng.
    
    Với mỗi block 8x8:
    1. Trích xuất 8-bit watermark từ các vị trí đã chọn theo secret_key + block_index (LSB)
    2. Tính lại CRC-8 checksum từ 56 pixels còn lại (dữ liệu)
    3. So sánh watermark trích xuất với checksum đã tính
    4. Đánh dấu block là tampered nếu không khớp
    
    Args:
        watermarked_path: Đường dẫn tới ảnh đã nhúng watermark.
        secret_key: Secret key (phải khớp với khi embed).
        
    Returns:
        Dictionary chứa kết quả xác minh:
        - tampered_blocks: Danh sách các (row, col) indices của block bị tampered
        - total_blocks: Tổng số blocks đã kiểm tra
        - tamper_count: Số blocks bị tampered
        - blocks_shape: Kích thước lưới blocks (num_rows, num_cols)
        - image_shape: Kích thước ảnh (height, width)
        - mode: Chế độ ảnh ('L', 'RGB', 'RGBA')
    """
    check_input_warning(watermarked_path)
    
    img_array, mode = load_image_full(watermarked_path)
    orig_height, orig_width = img_array.shape[:2]
    
    print(f"Đang xác minh ảnh: {orig_width}x{orig_height} (mode: {mode})")
    print(f"Secret key: {secret_key}")
    
    blue_channel = extract_blue_channel(img_array, mode)
    
    pad_h = (8 - orig_height % 8) % 8
    pad_w = (8 - orig_width % 8) % 8
    
    if pad_h > 0 or pad_w > 0:
        if mode == 'L':
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode='edge')
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w)), mode='edge')
        else:
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode='edge')
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w), (0, 0)), mode='edge')
    
    height, width = blue_channel.shape
    
    num_blocks_y = height // 8
    num_blocks_x = width // 8
    num_blocks = num_blocks_y * num_blocks_x
    
    print(f"Tổng số blocks: {num_blocks_x}x{num_blocks_y} = {num_blocks}")
    
    tampered_blocks = []
    verified_blocks = []
    
    for block_row in range(num_blocks_y):
        for block_col in range(num_blocks_x):
            block_idx = block_row * num_blocks_x + block_col
            
            watermark_positions = get_watermark_positions(block_idx, secret_key)
            
            watermark_pixels = get_watermark_pixels_from_block(
                blue_channel, block_row, block_col, watermark_positions
            )
            extracted_bits = np.array([extract_bit(int(p)) for p in watermark_pixels])
            extracted_checksum = binary_to_int(extracted_bits)
            
            data_pixels = get_data_pixels_for_block(
                img_array, mode, block_row, block_col, watermark_positions
            )
            
            block_data = data_pixels
            
            calculated_checksum = calculate_crc_checksum(
                block_data, mode, secret_key, block_idx
            )
            
            if extracted_checksum != calculated_checksum:
                tampered_blocks.append((block_row, block_col))
            else:
                verified_blocks.append((block_row, block_col))
    
    tamper_count = len(tampered_blocks)
    
    print(f"\nKết quả xác minh:")
    print(f"  Tổng số blocks: {num_blocks}")
    print(f"  Blocks OK: {len(verified_blocks)}")
    print(f"  Blocks bị tampered: {tamper_count}")
    
    if tamper_count > 0:
        print(f"  Tỷ lệ tampered: {100*tamper_count/num_blocks:.2f}%")
    
    return {
        'tampered_blocks': tampered_blocks,
        'total_blocks': num_blocks,
        'tamper_count': tamper_count,
        'verified_count': len(verified_blocks),
        'blocks_shape': (num_blocks_y, num_blocks_x),
        'image_shape': (height, width),
        'original_size': (orig_height, orig_width),
        'mode': mode
    }


def verify_and_generate_outputs(watermarked_path: str, 
                                  output_dir: str = "output",
                                  secret_key: str = DEFAULT_KEY) -> dict:
    """
    Xác minh watermark và tạo các ảnh output.
    
    Sinh ra:
    - tamper_mask.png: Mask nhị phân hiển thị các blocks bị tampered (trắng)
    - overlay.png: Ảnh gốc/watermarked với overlay đỏ trên các vùng bị tampered
    
    Args:
        watermarked_path: Đường dẫn tới ảnh đã nhúng watermark.
        output_dir: Thư mục lưu các ảnh output.
        secret_key: Secret key (phải khớp với khi embed).
        
    Returns:
        Dictionary kết quả xác minh.
    """
    results = verify_watermark(watermarked_path, secret_key)
    
    img_array, mode = load_image_full(watermarked_path)
    orig_height, orig_width = img_array.shape[:2]
    
    blue_channel = extract_blue_channel(img_array, mode)
    
    pad_h = (8 - orig_height % 8) % 8
    pad_w = (8 - orig_width % 8) % 8
    
    if pad_h > 0 or pad_w > 0:
        if mode == 'L':
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode='edge')
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w)), mode='edge')
        else:
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode='edge')
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w), (0, 0)), mode='edge')
    
    height, width = blue_channel.shape
    
    tamper_mask = create_tamper_mask(results['blocks_shape'], 
                                      results['tampered_blocks'])
    
    tamper_mask = tamper_mask[:height, :width]
    
    mask_path = f"{output_dir}/tamper_mask.png"
    Image.fromarray(tamper_mask).save(mask_path)
    print(f"\nĐã lưu tamper mask vào: {mask_path}")
    
    overlay = overlay_mask_on_image(img_array, tamper_mask)
    
    if pad_h > 0 or pad_w > 0:
        overlay = overlay[:orig_height, :orig_width, :]
    
    overlay_path = f"{output_dir}/overlay.png"
    Image.fromarray(overlay).save(overlay_path)
    print(f"Đã lưu overlay image vào: {overlay_path}")
    
    results['mask_path'] = mask_path
    results['overlay_path'] = overlay_path
    
    return results



# Hàm thêm vào với xử lý base64 không lưu file ảnh
def verify_and_generate_images(img_array, mode, secret_key: str):
    orig_height, orig_width = img_array.shape[:2]

    blue_channel = extract_blue_channel(img_array, mode)

    pad_h = (8 - orig_height % 8) % 8
    pad_w = (8 - orig_width % 8) % 8

    if pad_h > 0 or pad_w > 0:
        if mode == 'L':
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode='edge')
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w)), mode='edge')
        else:
            blue_channel = np.pad(blue_channel, ((0, pad_h), (0, pad_w)), mode='edge')
            img_array = np.pad(img_array, ((0, pad_h), (0, pad_w), (0, 0)), mode='edge')

    height, width = blue_channel.shape

    num_blocks_y = height // 8
    num_blocks_x = width // 8

    tampered_blocks = []
    verified_blocks = []

    for block_row in range(num_blocks_y):
        for block_col in range(num_blocks_x):
            block_idx = block_row * num_blocks_x + block_col

            watermark_positions = get_watermark_positions(block_idx, secret_key)

            watermark_pixels = get_watermark_pixels_from_block(
                blue_channel, block_row, block_col, watermark_positions
            )

            extracted_bits = np.array([extract_bit(int(p)) for p in watermark_pixels])
            extracted_checksum = binary_to_int(extracted_bits)

            data_pixels = get_data_pixels_for_block(
                img_array, mode, block_row, block_col, watermark_positions
            )

            calculated_checksum = calculate_crc_checksum(
                data_pixels, mode, secret_key, block_idx
            )

            if extracted_checksum != calculated_checksum:
                tampered_blocks.append((block_row, block_col))
            else:
                verified_blocks.append((block_row, block_col))

    tamper_mask = create_tamper_mask(
        (num_blocks_y, num_blocks_x),
        tampered_blocks
    )

    overlay = overlay_mask_on_image(img_array, tamper_mask)

    if pad_h > 0 or pad_w > 0:
        tamper_mask = tamper_mask[:orig_height, :orig_width]
        overlay = overlay[:orig_height, :orig_width]

    return {
        "tamper_count": len(tampered_blocks),
        "total_blocks": num_blocks_x * num_blocks_y,
        "verified_count": len(verified_blocks),
        "mask": tamper_mask,
        "overlay": overlay
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        watermarked_path = sys.argv[1]
        key = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_KEY
        verify_and_generate_outputs(watermarked_path, "output", key)
    else:
        print("Cách dùng: python verify.py <watermarked_image> [secret_key]")