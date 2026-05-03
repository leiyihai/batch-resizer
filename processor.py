import os
from PIL import Image

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}


def process_images(input_dir, output_dir, target_size, progress_callback=None):
    """Walk input_dir, resize every image to target_size, write to output_dir
    preserving directory structure and filenames.

    progress_callback(current, total) is called after each file.
    Returns (success_count, error_count, errors_list).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Collect all image files first so we know the total count
    image_files = []
    for root, _dirs, files in os.walk(input_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                image_files.append((root, f, ext))

    total = len(image_files)
    success = 0
    errors = []

    for idx, (src_root, filename, ext) in enumerate(image_files, start=1):
        src_path = os.path.join(src_root, filename)

        # Compute relative path from input_dir
        rel_dir = os.path.relpath(src_root, input_dir)
        dst_dir = os.path.join(output_dir, rel_dir)
        os.makedirs(dst_dir, exist_ok=True)

        dst_path = os.path.join(dst_dir, filename)

        try:
            img = Image.open(src_path)
            img = img.resize(target_size, Image.LANCZOS)
            # JPEG doesn't support alpha — convert transparent images to RGB
            if ext in ('.jpg', '.jpeg') and img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(dst_path)
            success += 1
        except Exception as e:
            errors.append(f"{src_path}: {e}")

        if progress_callback:
            progress_callback(idx, total)

    return success, total - success, errors
