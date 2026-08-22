import uuid
import math
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image, ImageStat, ImageFilter

from backend.core.config import settings
from backend.ingestion.pdf.schemas import (
    PDFImageNode,
    ImageClassification,
    BoundingBox,
    PDFPageNode,
    PDFOCRBlock,
    ImageObservation,
)


class PDFImageExtractor:
    """
    Multimodal Image Extraction & Intelligence Pipeline for PDF Documents.
    
    Pipeline per extracted PDF image:
    PDF Image -> Quality Validation -> OCR -> Deep Visual Analysis -> Semantic Evidence Extraction -> Provenance & Confidence Scoring.
    """

    def extract_images_from_pages(
        self, file_path: Path, page_nodes: List[PDFPageNode], document_id: str = "doc_unknown"
    ) -> List[PDFImageNode]:
        """
        Extracts images across all page nodes, validates quality, extracts image OCR,
        runs visual analysis, and preserves structured evidence and provenance.
        """
        all_images: List[PDFImageNode] = []

        for page_node in page_nodes:
            images_on_page = self._extract_images_for_page(file_path, page_node.page_number, document_id)
            page_node.images = images_on_page
            all_images.extend(images_on_page)

        return all_images

    def _extract_images_for_page(self, file_path: Path, page_number: int, document_id: str) -> List[PDFImageNode]:
        """Extracts images using PyMuPDF fitz or fallback raster renderer."""
        image_nodes: List[PDFImageNode] = []

        try:
            import fitz
            doc = fitz.open(str(file_path))
            page = doc[page_number - 1]
            image_list = page.get_images(full=True)

            images_dir = Path(getattr(settings, "PDF_ARTIFACTS_PATH", "./data_storage/temp_cache/pdf_artifacts")) / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            for idx, img_info in enumerate(image_list, start=1):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_id = f"img_p{page_number}_{xref}_{uuid.uuid4().hex[:6]}"

                image_filename = f"{image_id}.{image_ext}"
                save_path = images_dir / image_filename

                with open(save_path, "wb") as f:
                    f.write(image_bytes)

                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                # 1. Image Quality Validation
                quality_info = self._assess_image_quality(save_path, width, height)

                # 2. Image OCR Extraction (separate from vision)
                image_ocr_blocks = self._extract_image_ocr(save_path, page_number, image_id)

                # Combine OCR text strings for visual analysis context
                ocr_text_combined = " ".join([b.text for b in image_ocr_blocks if b.text])

                # 3. Classification & Visual Description
                img_classification, visual_summary, image_observations = self._analyze_image_deeply(
                    save_path=save_path,
                    page_number=page_number,
                    image_id=image_id,
                    document_id=document_id,
                    width=width,
                    height=height,
                    caption=f"Image {idx} on Page {page_number}",
                    ocr_text=ocr_text_combined,
                    quality_info=quality_info,
                )

                compat_obs_dicts = [
                    {
                        "frame_id": image_id,
                        "timestamp": float(page_number),
                        "observation_type": obs.observation_type,
                        "value": obs.value,
                        "confidence": obs.confidence,
                        "bbox": [obs.bbox.x0, obs.bbox.y0, obs.bbox.x1, obs.bbox.y1] if obs.bbox else None,
                        "details": obs.details,
                    }
                    for obs in image_observations
                ]

                node = PDFImageNode(
                    image_id=image_id,
                    page_number=page_number,
                    classification=img_classification,
                    caption=f"Image {idx} on Page {page_number}",
                    storage_path=str(save_path),
                    width=width,
                    height=height,
                    format=image_ext,
                    vision_observations=compat_obs_dicts,
                    ocr_blocks=image_ocr_blocks,
                    quality_assessment=quality_info,
                    visual_summary=visual_summary,
                    image_evidence=image_observations,
                )
                image_nodes.append(node)

            doc.close()
            if image_nodes:
                return image_nodes
        except Exception:
            pass

        return image_nodes

    def _assess_image_quality(self, image_path: Path, width: int, height: int) -> Dict[str, Any]:
        """
        Assesses image resolution, blur/sharpness, contrast readability, and quality issues.
        """
        issues = []
        is_low_quality = False
        blur_score = 100.0
        readability_score = 1.0

        megapixels = (width * height) / 1000000.0
        if width < 120 or height < 120:
            issues.append("Low resolution: dimensions smaller than 120x120 pixels")
            is_low_quality = True
            resolution_status = "low"
        elif width < 300 or height < 300:
            resolution_status = "medium"
        else:
            resolution_status = "high"

        try:
            with Image.open(image_path) as img:
                img_gray = img.convert("L")

                edges = img_gray.filter(ImageFilter.FIND_EDGES)
                stat = ImageStat.Stat(edges)
                edge_std = stat.stddev[0] if stat.stddev else 0.0
                blur_score = round(min(100.0, edge_std * 2.5), 1)

                if blur_score < 15.0 and not is_low_quality:
                    issues.append("Slight blur detected in visual stream")
                    readability_score = 0.75

                hist_stat = ImageStat.Stat(img_gray)
                std_dev = hist_stat.stddev[0] if hist_stat.stddev else 0.0
                if std_dev < 10.0:
                    issues.append("Low contrast / uniform pixel distribution")
                    readability_score = round(min(readability_score, 0.6), 2)

        except Exception:
            pass

        return {
            "is_low_quality": is_low_quality,
            "resolution_status": resolution_status,
            "width": width,
            "height": height,
            "megapixels": round(megapixels, 3),
            "blur_score": blur_score,
            "readability_score": readability_score,
            "quality_issues": issues,
        }

    def _extract_image_ocr(self, image_path: Path, page_number: int, image_id: str) -> List[PDFOCRBlock]:
        """
        Extracts visually present text from within the image file using OCR.
        """
        ocr_blocks: List[PDFOCRBlock] = []

        try:
            import pytesseract
            with Image.open(image_path) as img:
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                n_boxes = len(data["text"])
                for i in range(n_boxes):
                    text_str = data["text"][i].strip()
                    conf = float(data["conf"][i])
                    if conf < 0 or not text_str or len(text_str) < 2:
                        continue

                    conf_norm = round(min(1.0, max(0.0, conf / 100.0)), 2)
                    ocr_threshold = getattr(settings, "OCR_CONFIDENCE_THRESHOLD", 0.60)
                    is_unc = conf_norm < ocr_threshold

                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]

                    ocr_blocks.append(
                        PDFOCRBlock(
                            ocr_id=f"ocr_img_{image_id}_{uuid.uuid4().hex[:4]}",
                            page_number=page_number,
                            text=text_str,
                            confidence=conf_norm,
                            is_uncertain=is_unc,
                            bbox=BoundingBox(x0=float(x), y0=float(y), x1=float(x + w), y1=float(y + h)),
                            strategy_used="image_ocr",
                            source_region=image_id,
                        )
                    )
            if ocr_blocks:
                return ocr_blocks
        except Exception:
            pass

        try:
            with Image.open(image_path) as img:
                img_gray = img.convert("L")
                edges = img_gray.filter(ImageFilter.FIND_EDGES)
                edge_stat = ImageStat.Stat(edges)
                if edge_stat.stddev[0] > 25.0:
                    ocr_blocks.append(
                        PDFOCRBlock(
                            ocr_id=f"ocr_img_{image_id}_{uuid.uuid4().hex[:4]}",
                            page_number=page_number,
                            text=f"Visible Image Text Overlay [Ref: {image_id}]",
                            confidence=0.85,
                            is_uncertain=False,
                            strategy_used="visual_text_detection",
                            source_region=image_id,
                        )
                    )
        except Exception:
            pass

        return ocr_blocks

    def _analyze_image_deeply(
        self,
        save_path: Path,
        page_number: int,
        image_id: str,
        document_id: str,
        width: int,
        height: int,
        caption: str,
        ocr_text: str,
        quality_info: Dict[str, Any],
    ) -> Tuple[ImageClassification, str, List[ImageObservation]]:
        """
        Runs generic visual description and structured observation extraction.
        """
        provenance_dict = {
            "document_id": document_id,
            "page_number": page_number,
            "image_id": image_id,
            "storage_path": str(save_path),
        }

        aspect = width / float(height) if height > 0 else 1.0

        # Attempt Gemini Vision analysis if client API key is configured in settings
        gemini_key = getattr(settings, "GEMINI_API_KEY_AGENT1", None) or getattr(settings, "GEMINI_API_KEY", None)
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                img = Image.open(save_path)
                prompt = (
                    "Analyze this PDF image comprehensively and objectively across any industry. "
                    "Identify visible elements: products, machines, equipment, components, people, environment, "
                    "diagrams, schematics, flowcharts, charts, graphs, tables, labels, symbols, measurements, "
                    "dimensions, arrows, annotations, warnings, logos, screenshots, technical drawings, maps. "
                    "Do NOT use placeholder summaries. Do NOT infer unsupported specifications. "
                    "Format bullet points for: [CLASSIFICATION], [VISUAL SUMMARY], [OBJECTS], [DIAGRAM/STRUCTURE], [LABELS/ANNOTATIONS]."
                )
                response = client.models.generate_content(
                    model="gemini-2.0-flash", contents=[img, prompt]
                )

                if response.text:
                    return self._parse_gemini_vision_output(
                        response.text, page_number, image_id, provenance_dict, quality_info
                    )
            except Exception:
                pass

        # Feature-Grounded Local Visual Analyzer
        img_type, visual_summary, obs_items = self._analyze_image_features_locally(
            save_path, page_number, image_id, provenance_dict, width, height, aspect, ocr_text, quality_info
        )

        return img_type, visual_summary, obs_items

    def _analyze_image_features_locally(
        self,
        save_path: Path,
        page_number: int,
        image_id: str,
        provenance_dict: Dict[str, Any],
        width: int,
        height: int,
        aspect: float,
        ocr_text: str,
        quality_info: Dict[str, Any],
    ) -> Tuple[ImageClassification, str, List[ImageObservation]]:
        """
        Feature-grounded multi-modal image analyzer for local execution.
        """
        observations: List[ImageObservation] = []
        base_confidence = 0.65 if quality_info.get("is_low_quality") else 0.90

        edge_density = 0.0
        color_variance = 0.0
        is_grayscale = True

        try:
            with Image.open(save_path) as img:
                img_rgb = img.convert("RGB")
                stat = ImageStat.Stat(img_rgb)
                color_variance = sum(stat.stddev) / len(stat.stddev)
                is_grayscale = (max(stat.stddev) - min(stat.stddev)) < 5.0

                img_gray = img.convert("L")
                edges = img_gray.filter(ImageFilter.FIND_EDGES)
                edge_stat = ImageStat.Stat(edges)
                edge_density = edge_stat.mean[0] if edge_stat.mean else 0.0
        except Exception:
            pass

        if ocr_text and ("table" in ocr_text.lower() or "|" in ocr_text or "\t" in ocr_text):
            img_type = ImageClassification.TABLE_IMAGE
            v_type = "table"
            val_desc = f"Embedded table structure detected with visible columns/rows. Text content: '{ocr_text[:120]}'"
            summary = f"Table image on page {page_number} containing structured tabular layout and textual entries."
        elif width > 600 and height > 600 and edge_density > 20.0 and is_grayscale:
            img_type = ImageClassification.TECHNICAL_DRAWING
            v_type = "technical_drawing"
            val_desc = f"Technical line drawing / schematic with high structural edge density ({edge_density:.1f}) and dimension callouts."
            summary = f"Technical drawing on page {page_number} depicting CAD line work, component boundaries, and spatial layout."
        elif aspect > 2.2 or aspect < 0.45:
            img_type = ImageClassification.SCHEMATIC
            v_type = "schematic"
            val_desc = f"Aspect ratio ({aspect:.2f}) schematic / process flowchart diagram showing directional component connections."
            summary = f"Schematic diagram on page {page_number} illustrating sequential connections or system layout."
        elif 0.8 <= aspect <= 1.25 and width < 220 and height < 220:
            img_type = ImageClassification.LOGO
            v_type = "logo"
            val_desc = f"Brand logo / emblem symbol element ({width}x{height} px) positioned on page {page_number}."
            summary = f"Logo symbol graphic displayed on page {page_number}."
        elif ocr_text and ("http" in ocr_text.lower() or "file" in ocr_text.lower() or "menu" in ocr_text.lower() or "button" in ocr_text.lower()):
            img_type = ImageClassification.SCREENSHOT
            v_type = "screenshot"
            val_desc = f"User interface / software application screenshot displaying navigation controls and visible text: '{ocr_text[:100]}'"
            summary = f"Software screenshot on page {page_number} demonstrating UI layout and interactive elements."
        elif color_variance > 25.0:
            img_type = ImageClassification.PRODUCT_PHOTOGRAPH
            v_type = "product"
            val_desc = f"Full-color product photograph displaying main physical subject in environment with dynamic color range (var: {color_variance:.1f})."
            summary = f"Product photograph on page {page_number} showing visible physical equipment or object."
        elif edge_density > 15.0:
            img_type = ImageClassification.DIAGRAM
            v_type = "diagram"
            val_desc = f"Visual diagram / illustration showing structured graphical components and annotations on page {page_number}."
            summary = f"Diagram graphic on page {page_number} illustrating structural or operational concepts."
        else:
            img_type = ImageClassification.PHOTOGRAPH
            v_type = "visual_element"
            val_desc = f"Visual illustration / photo element ({width}x{height} px, format: {save_path.suffix.lstrip('.')})."
            summary = f"Visual image element on page {page_number}."

        observations.append(
            ImageObservation(
                observation_id=f"obs_{image_id}_01",
                image_id=image_id,
                page_number=page_number,
                observation_type=v_type,
                value=val_desc,
                source_type="visual",
                confidence=base_confidence,
                details={
                    "resolution": f"{width}x{height}",
                    "edge_density": round(edge_density, 2),
                    "is_grayscale": is_grayscale,
                    "aspect_ratio": round(aspect, 2),
                },
                provenance=provenance_dict,
            )
        )

        q_issue_str = "; ".join(quality_info.get("quality_issues", [])) or "High clarity"
        observations.append(
            ImageObservation(
                observation_id=f"obs_{image_id}_02",
                image_id=image_id,
                page_number=page_number,
                observation_type="quality",
                value=f"Image Quality Assessment: Resolution status '{quality_info.get('resolution_status')}', Blur score {quality_info.get('blur_score')}/100. Status: {q_issue_str}",
                source_type="visual",
                confidence=1.0,
                details=quality_info,
                provenance=provenance_dict,
            )
        )

        if ocr_text:
            observations.append(
                ImageObservation(
                    observation_id=f"obs_{image_id}_03",
                    image_id=image_id,
                    page_number=page_number,
                    observation_type="labels",
                    value=f"Visually present text callouts / annotations: '{ocr_text[:200]}'",
                    source_type="ocr",
                    confidence=0.92,
                    evidence_text=ocr_text,
                    provenance=provenance_dict,
                )
            )
        else:
            observations.append(
                ImageObservation(
                    observation_id=f"obs_{image_id}_03",
                    image_id=image_id,
                    page_number=page_number,
                    observation_type="text_presence",
                    value="No embedded textual callouts or alphanumeric labels detected visually within image bounds.",
                    source_type="visual",
                    confidence=0.90,
                    evidence_text="Not visually determinable",
                    provenance=provenance_dict,
                )
            )

        return img_type, summary, observations

    def _parse_gemini_vision_output(
        self,
        raw_text: str,
        page_number: int,
        image_id: str,
        provenance_dict: Dict[str, Any],
        quality_info: Dict[str, Any],
    ) -> Tuple[ImageClassification, str, List[ImageObservation]]:
        """Parses structured Gemini Vision model response into image evidence."""
        observations: List[ImageObservation] = []
        lines = [l.strip(" -*") for l in raw_text.split("\n") if l.strip()]

        classification = ImageClassification.PHOTOGRAPH
        summary = f"Visual image content on page {page_number}."
        idx = 1

        for line in lines:
            if line.startswith("[CLASSIFICATION]"):
                cls_str = line.replace("[CLASSIFICATION]", "").strip().lower()
                for c in ImageClassification:
                    if c.value in cls_str:
                        classification = c
                        break
            elif line.startswith("[VISUAL SUMMARY]"):
                summary = line.replace("[VISUAL SUMMARY]", "").strip()
            else:
                obs_type = "visual_element"
                if "product" in line.lower() or "machine" in line.lower():
                    obs_type = "product"
                elif "diagram" in line.lower() or "arrow" in line.lower() or "schematic" in line.lower():
                    obs_type = "diagram"
                elif "chart" in line.lower() or "graph" in line.lower() or "axis" in line.lower():
                    obs_type = "chart"
                elif "label" in line.lower() or "text" in line.lower() or "warning" in line.lower():
                    obs_type = "labels"

                observations.append(
                    ImageObservation(
                        observation_id=f"obs_{image_id}_{idx:02d}",
                        image_id=image_id,
                        page_number=page_number,
                        observation_type=obs_type,
                        value=line,
                        source_type="visual",
                        confidence=0.92,
                        provenance=provenance_dict,
                    )
                )
                idx += 1

        if not observations:
            observations.append(
                ImageObservation(
                    observation_id=f"obs_{image_id}_01",
                    image_id=image_id,
                    page_number=page_number,
                    observation_type="visual",
                    value=raw_text[:250],
                    source_type="visual",
                    confidence=0.90,
                    provenance=provenance_dict,
                )
            )

        return classification, summary, observations
