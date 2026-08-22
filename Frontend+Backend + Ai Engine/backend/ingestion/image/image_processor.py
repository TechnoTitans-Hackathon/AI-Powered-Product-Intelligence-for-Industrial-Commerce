"""Image Preprocessing and Validation Engine."""

from __future__ import annotations

import io
import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError

from .config import config
from .schemas import ImageMetadata


class ImageProcessingError(Exception):
    """Custom exception for image validation and processing failures."""
    def __init__(self, message: str, code: str = "INVALID_IMAGE"):
        super().__init__(message)
        self.message = message
        self.code = code


class ImageProcessor:
    """
    Validates, inspects, and prepares industrial product images for OCR and Vision analysis.
    Provides region detection and OCR image crop enhancement.
    """

    def __init__(
        self,
        max_file_size_bytes: int = config.MAX_FILE_SIZE_BYTES,
        max_dimension_px: int = config.MAX_DIMENSION_PX,
        min_dimension_px: int = config.MIN_DIMENSION_PX,
    ):
        self.max_file_size_bytes = max_file_size_bytes
        self.max_dimension_px = max_dimension_px
        self.min_dimension_px = min_dimension_px

    def validate_and_process(
        self,
        image_bytes: bytes,
        filename: str = "upload.jpg",
        content_type: Optional[str] = None,
    ) -> Tuple[bytes, ImageMetadata]:
        """
        Validates the raw image bytes, checks size and format constraints,
        and optionally resizes very large images while preserving aspect ratio.

        Returns:
            (processed_image_bytes, ImageMetadata)
        """
        # 1. Check size constraints
        if not image_bytes:
            raise ImageProcessingError("Uploaded file is empty (0 bytes).", code="EMPTY_FILE")

        size_bytes = len(image_bytes)
        if size_bytes > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            raise ImageProcessingError(
                f"File size ({size_bytes / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB.",
                code="FILE_TOO_LARGE",
            )

        # 2. Check file extension
        ext = os.path.splitext(filename)[1].lower() if filename else ""
        if ext and ext not in config.ALLOWED_EXTENSIONS:
            raise ImageProcessingError(
                f"Unsupported file extension '{ext}'. Supported formats: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}",
                code="UNSUPPORTED_FORMAT",
            )

        # 3. Check content-type if provided
        if content_type and content_type.lower() not in config.ALLOWED_MIME_TYPES:
            # If extension is valid, allow MIME check to proceed, otherwise reject
            if not ext or ext not in config.ALLOWED_EXTENSIONS:
                raise ImageProcessingError(
                    f"Unsupported MIME type '{content_type}'.",
                    code="UNSUPPORTED_MIME_TYPE",
                )

        # 4. Open and verify image structure using PIL
        try:
            image_stream = io.BytesIO(image_bytes)
            img = Image.open(image_stream)
            img.load()  # Force decoding to detect corruption early
        except (UnidentifiedImageError, OSError, ValueError) as e:
            raise ImageProcessingError(
                f"The uploaded file is not a valid or readable image: {str(e)}",
                code="CORRUPTED_IMAGE",
            )

        orig_w, orig_h = img.size
        img_format = (img.format or ext.replace(".", "").upper() or "JPEG").upper()
        color_mode = img.mode

        # 5. Check minimum dimensions
        if orig_w < self.min_dimension_px or orig_h < self.min_dimension_px:
            raise ImageProcessingError(
                f"Image dimensions ({orig_w}x{orig_h}) are smaller than minimum allowed ({self.min_dimension_px}x{self.min_dimension_px}).",
                code="IMAGE_TOO_SMALL",
            )

        # 6. Normalize and resize if dimensions exceed max_dimension_px
        resized = False
        final_w, final_h = orig_w, orig_h
        output_bytes = image_bytes

        if max(orig_w, orig_h) > self.max_dimension_px:
            ratio = self.max_dimension_px / float(max(orig_w, orig_h))
            final_w = int(orig_w * ratio)
            final_h = int(orig_h * ratio)

            # High-quality Lanczos resampling
            resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
            img_resized = img.resize((final_w, final_h), resample=resample_filter)
            resized = True

            # Save resized image back to bytes in matching format
            out_stream = io.BytesIO()
            save_format = "PNG" if img_format == "PNG" else "JPEG"
            if save_format == "JPEG" and img_resized.mode in ("RGBA", "P", "LA"):
                # Convert alpha to white background for JPEG
                background = Image.new("RGB", img_resized.size, (255, 255, 255))
                if img_resized.mode == "RGBA":
                    background.paste(img_resized, mask=img_resized.split()[3])
                else:
                    background.paste(img_resized.convert("RGB"))
                img_resized = background

            img_resized.save(out_stream, format=save_format, quality=95)
            output_bytes = out_stream.getvalue()

        # 7. Construct metadata
        metadata = ImageMetadata(
            width=final_w,
            height=final_h,
            format=img_format,
            size_bytes=len(output_bytes),
            channels=color_mode,
            color_mode=color_mode,
            aspect_ratio=round(final_w / float(final_h), 3) if final_h > 0 else 1.0,
            resized=resized,
            original_dimensions=(orig_w, orig_h) if resized else None,
        )

        return output_bytes, metadata

    def detect_text_regions(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Detects candidate text-bearing regions (such as nameplates, specification tables,
        brand markings, serial plates, small text blocks, stickers, warning labels).

        Returns:
            List of dicts: [{
                "region_id": str,
                "region_type": str,
                "bbox": [x, y, w, h],
                "bounding_box": [x, y, x+w, y+h],
                "confidence": float,
                "crop_bytes": bytes,
                "is_small_text": bool
            }]
        """
        regions: List[Dict[str, Any]] = []
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return regions

            h_img, w_img = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Multiple kernel shapes for nameplates vs lines vs small text
            kernels = [
                (cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5)), "standard"),
                (cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3)), "wide_line"),
                (cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)), "block_table"),
            ]

            candidate_boxes = []
            for kernel, k_type in kernels:
                grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
                _, bw = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5) if k_type == "wide_line" else (15, 7))
                connected = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, close_k)

                contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    x, y, w, h = cv2.boundingRect(cnt)
                    area = w * h
                    area_ratio = area / float(w_img * h_img)
                    aspect = w / float(h) if h > 0 else 0

                    if area > 150 and area_ratio < 0.9 and w > 15 and h > 8 and 0.15 <= aspect <= 25.0:
                        candidate_boxes.append((x, y, w, h, k_type))

            # Merging overlapping boxes
            merged_boxes = self._merge_overlapping_boxes(candidate_boxes, w_img, h_img)

            idx = 1
            for x, y, w, h, k_type in merged_boxes:
                margin_x = int(w * 0.05)
                margin_y = int(h * 0.05)
                x1 = max(0, x - margin_x)
                y1 = max(0, y - margin_y)
                x2 = min(w_img, x + w + margin_x)
                y2 = min(h_img, y + h + margin_y)
                crop_w, crop_h = x2 - x1, y2 - y1

                if crop_w > 15 and crop_h > 8:
                    crop_np = img[y1:y2, x1:x2]
                    success, encoded_crop = cv2.imencode('.jpg', crop_np, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                    if success:
                        aspect = crop_w / float(crop_h) if crop_h > 0 else 0
                        is_small = crop_h < 40 or (crop_w * crop_h) < (w_img * h_img * 0.05)

                        if aspect > 3.0:
                            r_type = "specification_nameplate"
                        elif crop_h > 100:
                            r_type = "specification_table"
                        elif is_small:
                            r_type = "small_text_block"
                        else:
                            r_type = "product_label"

                        regions.append({
                            "region_id": f"text_region_{idx:02d}",
                            "region_type": r_type,
                            "bbox": [x1, y1, crop_w, crop_h],
                            "bounding_box": [x1, y1, x2, y2],
                            "confidence": round(0.85 if is_small else 0.92, 2),
                            "crop_bytes": encoded_crop.tobytes(),
                            "is_small_text": is_small,
                        })
                        idx += 1

            regions.sort(key=lambda r: r["bbox"][2] * r["bbox"][3], reverse=True)
            return regions[:8]

        except Exception:
            return regions

    def _merge_overlapping_boxes(self, boxes: List[Tuple[int, int, int, int, str]], w_img: int, h_img: int) -> List[Tuple[int, int, int, int, str]]:
        """Merges redundant bounding boxes."""
        if not boxes:
            return []
        
        boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
        merged = []

        for b in boxes:
            x1, y1, w1, h1, k1 = b
            overlap = False
            for i, m in enumerate(merged):
                x2, y2, w2, h2, k2 = m
                inter_x1 = max(x1, x2)
                inter_y1 = max(y1, y2)
                inter_x2 = min(x1 + w1, x2 + w2)
                inter_y2 = min(y1 + h1, y2 + h2)

                inter_w = max(0, inter_x2 - inter_x1)
                inter_h = max(0, inter_y2 - inter_y1)
                inter_area = inter_w * inter_h
                min_area = min(w1 * h1, w2 * h2)

                if min_area > 0 and (inter_area / float(min_area)) > 0.65:
                    nx1 = min(x1, x2)
                    ny1 = min(y1, y2)
                    nx2 = max(x1 + w1, x2 + w2)
                    ny2 = max(y1 + h1, y2 + h2)
                    merged[i] = (nx1, ny1, nx2 - nx1, ny2 - ny1, k2)
                    overlap = True
                    break

            if not overlap:
                merged.append(b)

        return merged

    def extract_line_crops(self, crop_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extracts horizontal line crops from multi-line text blocks or specification tables.
        Allows line-by-line high-resolution OCR for dense specification nameplates.
        """
        line_crops = []
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(crop_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return line_crops

            h_crop, w_crop = img.shape[:2]
            if h_crop < 30:
                return line_crops

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

            proj = np.sum(bw, axis=1)

            in_line = False
            start_y = 0
            lines_coords = []

            for y, val in enumerate(proj):
                if val > (w_crop * 8) and not in_line:
                    in_line = True
                    start_y = max(0, y - 2)
                elif val <= (w_crop * 8) and in_line:
                    in_line = False
                    end_y = min(h_crop, y + 2)
                    if (end_y - start_y) >= 6:
                        lines_coords.append((start_y, end_y))

            if in_line and (h_crop - start_y) >= 6:
                lines_coords.append((start_y, h_crop))

            for idx, (sy, ey) in enumerate(lines_coords, start=1):
                line_img = img[sy:ey, 0:w_crop]
                success, encoded_line = cv2.imencode('.jpg', line_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                if success:
                    line_crops.append({
                        "line_id": f"line_{idx:02d}",
                        "bbox": [0, sy, w_crop, ey - sy],
                        "crop_bytes": encoded_line.tobytes(),
                    })

            return line_crops
        except Exception:
            return line_crops

    def generate_preprocessing_variants(
        self,
        crop_bytes: bytes,
        is_small_text: bool = False,
    ) -> Dict[str, bytes]:
        """
        Generates adaptive preprocessing variants for OCR pass comparison:
        - upscaled: High-ratio Lanczos upscale (3x-4x for small text)
        - contrast_enhanced: Grayscale + CLAHE / Contrast boost
        - adaptive_thresh: Otsu / Adaptive Binarization
        - denoised_sharpened: Non-local means denoising & sharpening
        """
        variants: Dict[str, bytes] = {}
        try:
            scale_factor = 3.5 if is_small_text else 2.0
            variants["upscaled"] = self.preprocess_image_crop(crop_bytes, scale_factor=scale_factor, enhance=False)
            variants["contrast_enhanced"] = self.preprocess_image_crop(crop_bytes, scale_factor=scale_factor, enhance=True)

            import cv2
            import numpy as np

            nparr = np.frombuffer(variants["contrast_enhanced"], np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

            if img is not None:
                adapt_thresh = cv2.adaptiveThreshold(
                    img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
                )
                success_thresh, enc_thresh = cv2.imencode('.jpg', adapt_thresh)
                if success_thresh:
                    variants["adaptive_thresh"] = enc_thresh.tobytes()

                denoised = cv2.fastNlMeansDenoising(img, h=10, templateWindowSize=7, searchWindowSize=21)
                kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
                success_sharp, enc_sharp = cv2.imencode('.jpg', sharpened)
                if success_sharp:
                    variants["denoised_sharpened"] = enc_sharp.tobytes()

            return variants
        except Exception:
            variants["default"] = crop_bytes
            return variants

    def preprocess_image_crop(
        self,
        image_bytes: bytes,
        bbox: Optional[List[int]] = None,
        rotation: int = 0,
        enhance: bool = True,
        scale_factor: float = 2.0,
    ) -> bytes:
        """
        Preprocesses an image or crop for optimal OCR extraction:
        - Crop if bbox provided [x, y, w, h]
        - Upscale small crops with specified scale_factor
        - Grayscale conversion
        - Contrast enhancement & Sharpening
        - Orientation rotation handling (0, 90, 180, 270)
        """
        try:
            image_stream = io.BytesIO(image_bytes)
            img = Image.open(image_stream)

            if bbox and len(bbox) == 4:
                x, y, w, h = bbox
                img = img.crop((x, y, x + w, y + h))

            if rotation in (90, 180, 270):
                img = img.rotate(rotation, expand=True)

            if img.mode != "RGB":
                img = img.convert("RGB")

            w, h = img.size
            if w < 400 or h < 400 or scale_factor > 1.0:
                scale = max(scale_factor, 500.0 / float(max(w, h, 1)))
                new_w, new_h = int(w * scale), int(h * scale)
                resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
                img = img.resize((new_w, new_h), resample=resample_filter)

            if enhance:
                img_gray = img.convert("L")
                enhancer = ImageEnhance.Contrast(img_gray)
                img_enhanced = enhancer.enhance(1.8)
                img_final = img_enhanced.filter(ImageFilter.SHARPEN)
            else:
                img_final = img

            out_stream = io.BytesIO()
            img_final.save(out_stream, format="JPEG", quality=95)
            return out_stream.getvalue()

        except Exception:
            return image_bytes

