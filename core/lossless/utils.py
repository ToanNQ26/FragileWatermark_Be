"""
Các hàm tiện ích cho hệ thống fragile watermarking.
Hỗ trợ cả ảnh grayscale (L) và ảnh màu (RGB, RGBA).
"""
import os
import numpy as np
from PIL import Image


LOSSLESS_FORMATS = {'.png', '.bmp', '.tif', '.tiff'}
LOSSLY_FORMATS = {'.jpg', '.jpeg', '.jpe', '.jfif'}


def is_lossless_format(path: str) -> bool:
    """
    Kiểm tra xem đường dẫn có định dạng lossless hay không.
    
    Args:
        path: Đường dẫn file.
        
    Returns:
        True nếu định dạng lossless, False nếu lossy.
    """
    _, ext = os.path.splitext(path)
    return ext.lower() in LOSSLESS_FORMATS


def is_lossy_format(path: str) -> bool:
    """
    Kiểm tra xem đường dẫn có định dạng lossy hay không.
    
    Args:
        path: Đường dẫn file.
        
    Returns:
        True nếu định dạng lossy, False nếu lossless.
    """
    _, ext = os.path.splitext(path)
    return ext.lower() in LOSSLY_FORMATS


def validate_output_format(output_path: str) -> None:
    """
    Kiểm tra định dạng output. Nếu là lossy thì raise ValueError.
    
    Args:
        output_path: Đường dẫn file output.
        
    Raises:
        ValueError: Nếu định dạng không phù hợp (lossy).
    """
    if is_lossy_format(output_path):
        raise ValueError(
            f"LỖI: Định dạng '{os.path.splitext(output_path)[1]}' là định dạng lossy (mất dữ liệu). "
            f"Watermark LSB sẽ bị phá hủy khi nén JPEG. "
            f"Vui lòng sử dụng định dạng lossless như: {', '.join(LOSSLESS_FORMATS)}"
        )
    if not is_lossless_format(output_path):
        raise ValueError(
            f"LỖI: Định dạng '{os.path.splitext(output_path)[1]}' không được hỗ trợ. "
            f"Chỉ hỗ trợ: {', '.join(LOSSLESS_FORMATS)}"
        )


def check_input_warning(path: str) -> bool:
    """
    Kiểm tra input và in cảnh báo nếu là JPEG/JPG.
    
    Args:
        path: Đường dẫn file input.
        
    Returns:
        True nếu là định dạng lossy, False nếu lossless.
    """
    if is_lossy_format(path):
        print(f"\n⚠️  CẢNH BÁO: Ảnh đầu vào là JPEG/JPG (định dạng lossy)")
        print("   Watermark LSB có thể đã bị mất do nén JPEG.")
        print("   Kết quả xác minh có thể KHÔNG đáng tin cậy.")
        return True
    return False


def load_image_full(path: str) -> tuple:
    """
    Đọc ảnh từ file và giữ nguyên mode gốc.
    
    Args:
        path: Đường dẫn tới file ảnh.
        
    Returns:
        Tuple của (image_array, mode):
        - image_array: Numpy array (2D cho L, 3D cho RGB/RGBA)
        - mode: Chế độ ảnh ('L', 'RGB', 'RGBA')
    """
    img = Image.open(path)

    # --- BỔ SUNG XỬ LÝ MODE ---
    # Một số ảnh PNG có mode 'P' (palette), cần convert về RGB/RGBA
    if img.mode == 'P':
        if 'transparency' in img.info:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

    # Các mode khác không hỗ trợ → đưa về chuẩn
    elif img.mode not in ('L', 'RGB', 'RGBA'):
        if 'A' in img.mode:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
    # --- KẾT THÚC BỔ SUNG ---

    mode = img.mode
    return np.array(img, dtype=np.uint8), mode


def extract_blue_channel(img_array: np.ndarray, mode: str) -> np.ndarray:
    """
    Trích xuất kênh Blue từ ảnh để xử lý watermark.
    
    Args:
        img_array: Mảng ảnh đầy đủ.
        mode: Chế độ ảnh ('L', 'RGB', 'RGBA').
        
    Returns:
        Mảng 2D grayscale (kênh Blue hoặc ảnh gốc nếu là L).
    """
    if mode == 'L':
        return img_array.copy()
    elif mode in ('RGB', 'RGBA'):
        return img_array[:, :, 2].copy()
    else:
        raise ValueError(f"Mode không được hỗ trợ: {mode}")


def merge_blue_channel(img_array: np.ndarray, mode: str, blue_channel: np.ndarray) -> np.ndarray:
    """
    Ghép kênh Blue đã xử lý vào ảnh gốc.
    
    Args:
        img_array: Mảng ảnh gốc.
        mode: Chế độ ảnh ('L', 'RGB', 'RGBA').
        blue_channel: Kênh Blue đã xử lý (2D array).
        
    Returns:
        Mảng ảnh đã ghép với kênh Blue mới.
    """
    if mode == 'L':
        return blue_channel.copy()
    elif mode in ('RGB', 'RGBA'):
        result = img_array.copy()
        result[:, :, 2] = blue_channel
        return result
    else:
        raise ValueError(f"Mode không được hỗ trợ: {mode}")


def load_image(path: str) -> np.ndarray:
    """
    Đọc ảnh từ file và chuyển sang grayscale dạng numpy array.
    (Giữ lại cho backward compatibility)
    
    Args:
        path: Đường dẫn tới file ảnh.
        
    Returns:
        Ảnh grayscale dạng numpy array (ma trận 2D uint8).
    """
    img = Image.open(path)
    if img.mode != 'L':
        img = img.convert('L')
    return np.array(img, dtype=np.uint8)


def save_image(path: str, img: np.ndarray) -> None:
    """
    Lưu numpy array thành file ảnh.
    
    Args:
        path: Đường dẫn file output.
        img: Numpy array (2D cho grayscale, 3D cho màu).
    """
    if len(img.shape) == 3 and img.shape[2] == 4:
        mode = 'RGBA'
    elif len(img.shape) == 3:
        mode = 'RGB'
    else:
        mode = 'L'
    Image.fromarray(img.astype(np.uint8), mode=mode).save(path)


def save_image_grayscale(path: str, img: np.ndarray) -> None:
    """
    Lưu numpy array grayscale thành file ảnh.
    (Giữ lại cho backward compatibility)
    
    Args:
        path: Đường dẫn file output.
        img: Numpy array 2D (grayscale).
    """
    Image.fromarray(img.astype(np.uint8)).save(path)


CRC8_POLYNOMIAL = 0x07


def crc8(data: bytes, polynomial: int = CRC8_POLYNOMIAL) -> int:
    """
    Tính CRC-8 cho dữ liệu.
    Dùng polynomial x^8 + x^2 + x + 1 (0x07) - phổ biến trong các hệ thống nhúng.
    
    CRC-8 tốt hơn tổng % 256 vì:
    - Phát hiện lỗi tốt hơn, đặc biệt là các lỗi burst
    - Khả năng phát hiện thay đổi đơn bit cao hơn
    - ít va chạm hơn so với simple sum
    
    Args:
        data: Dữ liệu cần tính CRC (bytes).
        polynomial: Polynomial CRC (mặc định 0x07).
        
    Returns:
        Giá trị CRC-8 (0-255).
    """
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




def calculate_crc_checksum(block_data: np.ndarray, mode: str, 
                                  secret_key: str = "", block_index: int = 0) -> int:
    """
    Tính CRC-8 từ toàn bộ dữ liệu block (đã loại watermark).

    block_data:
        - L: shape (56,)
        - RGB: shape (56, 3)
        - RGBA: shape (56, 4)
    """
    if block_data.ndim == 1:
        data_bytes = block_data.astype(np.uint8).tobytes()
    else:
        data_bytes = block_data.astype(np.uint8).flatten().tobytes()

    key_bytes = secret_key.encode('utf-8') if secret_key else b''
    block_idx_bytes = block_index.to_bytes(4, 'little')

    combined = key_bytes + block_idx_bytes + data_bytes
    return crc8(combined)


DEFAULT_KEY = "default_fragile_key"


def get_watermark_positions(block_index: int, secret_key: str = DEFAULT_KEY) -> list:
    """
    Xác định vị trí 8 pixels trong block dùng để nhúng watermark.
    Dùng secret_key + block_index để tạo vị trí deterministic.
    
    Vị trí được chọn dựa trên deterministic mapping:
    - Tạo một permutation từ key và block index
    - Chọn 8 vị trí duy nhất từ 64 vị trí trong block
    
    Args:
        block_index: Index của block.
        secret_key: Secret key.
        
    Returns:
        List của 8 tuple (row, col) vị trí trong block 8x8.
    """
    key_str = f"{secret_key}_{block_index}"
    seed = sum(ord(c) for c in key_str) * 256 + block_index
    
    rng = np.random.RandomState(seed)
    positions = rng.choice(64, size=8, replace=False)
    
    result = []
    for pos in positions:
        row = pos // 8
        col = pos % 8
        result.append((row, col))
    
    return result


def get_data_pixels_for_block(img_array: np.ndarray, mode: str, 
                                block_row: int, block_col: int,
                                watermark_positions: list) -> np.ndarray:
    """
    Lấy 56 pixel dữ liệu từ block, loại trừ các vị trí chứa watermark.

    Returns:
        - L: shape (56,)
        - RGB: shape (56, 3)
        - RGBA: shape (56, 4)
    """
    r_start = block_row * 8
    r_end = (block_row + 1) * 8
    c_start = block_col * 8
    c_end = (block_col + 1) * 8

    if mode == 'L':
        block = img_array[r_start:r_end, c_start:c_end]
        flat = block.reshape(-1)  # (64,)
        
        mask = np.ones(64, dtype=bool)
        for row, col in watermark_positions:
            mask[row * 8 + col] = False
        
        return flat[mask]  # (56,)

    else:
        block = img_array[r_start:r_end, c_start:c_end, :]
        channels = block.shape[2]
        
        flat = block.reshape(-1, channels)  # (64, C)
        
        mask = np.ones(64, dtype=bool)
        for row, col in watermark_positions:
            mask[row * 8 + col] = False
        
        return flat[mask]  # (56, C)


def get_watermark_pixels_from_block(blue_channel: np.ndarray, 
                                    block_row: int, block_col: int,
                                    watermark_positions: list) -> np.ndarray:
    """
    Lấy 8 pixel chứa watermark từ block.
    
    Args:
        blue_channel: Kênh Blue (hoặc ảnh L).
        block_row: Chỉ số hàng block.
        block_col: Chỉ số cột block.
        watermark_positions: List 8 vị trí chứa watermark.
        
    Returns:
        Mảng 8 giá trị pixel.
    """
    r_start = block_row * 8
    c_start = block_col * 8
    
    pixels = []
    for row, col in watermark_positions:
        pixels.append(blue_channel[r_start + row, c_start + col])
    
    return np.array(pixels, dtype=np.uint8)











def int_to_binary(n: int) -> np.ndarray:
    """
    Chuyển một số nguyên (0-255) thành mảng nhị phân 8 bit.
    
    Args:
        n: Giá trị số nguyên (0-255).
        
    Returns:
        Mảng 8 bit (0 hoặc 1).
    """
    return np.array([int(b) for b in format(n, '08b')], dtype=np.uint8)


def binary_to_int(bits: np.ndarray) -> int:
    """
    Chuyển mảng nhị phân 8 bit thành số nguyên.
    
    Args:
        bits: Mảng 8 bit.
        
    Returns:
        Giá trị số nguyên (0-255).
    """
    return int(''.join(str(b) for b in bits), 2)


def embed_bit(pixel_value: int, bit: int) -> int:
    """
    Nhúng 1 bit vào pixel sử dụng LSB.
    Xóa LSB và đặt thành bit mục tiêu.
    
    Args:
        pixel_value: Giá trị pixel gốc (0-255).
        bit: Bit cần nhúng (0 hoặc 1).
        
    Returns:
        Giá trị pixel đã được nhúng bit.
    """
    return (pixel_value & 0xFE) | bit


def extract_bit(pixel_value: int) -> int:
    """
    Trích xuất 1 bit từ LSB của pixel.
    
    Args:
        pixel_value: Giá trị pixel (0-255).
        
    Returns:
        Bit được trích xuất (0 hoặc 1).
    """
    return pixel_value & 1





def create_tamper_mask(blocks_shape: tuple, tampered_blocks: list) -> np.ndarray:
    """
    Tạo ảnh mask nhị phân cho các vùng bị giả mạo.
    Các block bị tampered hiển thị trắng (255), các block còn lại đen (0).
    
    Args:
        blocks_shape: (num_blocks_y, num_blocks_x) - kích thước lưới block.
        tampered_blocks: Danh sách các (row, col) indices của block bị tampered.
        
    Returns:
        Ảnh mask nhị phân (0 cho OK, 255 cho tampered).
    """
    mask = np.zeros((blocks_shape[0] * 8, blocks_shape[1] * 8), dtype=np.uint8)
    
    for row, col in tampered_blocks:
        mask[row*8:(row+1)*8, col*8:(col+1)*8] = 255
    
    return mask


def overlay_mask_on_image(image: np.ndarray, mask: np.ndarray, 
                          original_color=(0, 0, 255), tampered_color=(255, 0, 0)) -> np.ndarray:
    """
    Tạo ảnh overlay hiển thị vùng gốc và vùng bị giả mạo.
    Hỗ trợ cả ảnh grayscale và ảnh màu (RGB, RGBA).
    
    Args:
        image: Ảnh gốc (grayscale, RGB, hoặc RGBA).
        mask: Mask nhị phân (0 cho OK, 255 cho tampered).
        original_color: Tuple RGB cho vùng OK (mặc định xanh dương).
        tampered_color: Tuple RGB cho vùng tampered (mặc định đỏ).
        
    Returns:
        Ảnh RGB có overlay (loại bỏ alpha).
    """
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
