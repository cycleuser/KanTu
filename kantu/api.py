"""Unified API for KanTu with ToolResult pattern."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from kantu.core import DeltaType, ImageRecord, KanTuCore


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def init_gallery(path: str = ".") -> ToolResult:
    try:
        core = KanTuCore(path)
        if core.is_initialized():
            return ToolResult(
                success=True,
                data={"path": str(core.gallery_path)},
                error=None,
                metadata={"message": "Gallery already initialized"},
            )
        core.init_gallery()
        return ToolResult(
            success=True,
            data={"path": str(core.gallery_path)},
            error=None,
            metadata={"message": "Gallery initialized successfully"},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def add_image(
    image_path: str,
    gallery_path: str = ".",
    similarity_threshold: Optional[float] = None,
    force_base: bool = False,
) -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(
                success=False, error="Gallery not initialized. Run 'kantu init' first."
            )
        core._load_config()
        if similarity_threshold is not None:
            core.config.similarity_threshold = similarity_threshold
        if not Path(image_path).exists():
            return ToolResult(success=False, error=f"Image not found: {image_path}")
        image_id = core.compute_id(image_path)
        existing = core.get_image_record(image_id)
        if existing:
            return ToolResult(
                success=True,
                data={"id": image_id, "status": "already_exists"},
                metadata={"message": "Image already in gallery"},
            )
        phash = core.compute_hash(image_path)
        width, height = core.get_image_dimensions(image_path)
        original_size = core.get_file_size(image_path)
        if force_base:
            base_path = core.save_base_image(image_path, image_id)
            record = ImageRecord(
                id=image_id,
                phash=phash,
                original_path=str(Path(image_path).resolve()),
                is_base=True,
                width=width,
                height=height,
                file_size=original_size,
            )
            core.add_image_record(record)
            return ToolResult(
                success=True,
                data={"id": image_id, "type": "base", "path": base_path},
                metadata={"message": "Image added as base (forced)"},
            )
        similar = core.find_similar_images(phash)
        best_match = None
        best_ssim = 0
        for candidate in similar:
            if candidate["id"] == image_id:
                continue
            ssim_score = core.compute_ssim(image_path, candidate["original_path"])
            if ssim_score > best_ssim and ssim_score >= core.config.similarity_threshold:
                best_ssim = ssim_score
                best_match = candidate
        if best_match:
            delta, target_size = core.compute_pixel_delta(best_match["original_path"], image_path)
            delta_compressed = core.save_delta(delta, image_id)
            delta_size = core.get_file_size(delta_compressed)
            savings_ratio = 1 - (delta_size / original_size)
            if savings_ratio >= core.config.min_delta_ratio:
                record = ImageRecord(
                    id=image_id,
                    phash=phash,
                    original_path=str(Path(image_path).resolve()),
                    is_base=False,
                    base_id=best_match["id"],
                    delta_type=DeltaType.PIXEL,
                    delta_path=delta_compressed,
                    width=width,
                    height=height,
                    file_size=delta_size,
                    similarity_score=best_ssim,
                )
                core.add_image_record(record)
                return ToolResult(
                    success=True,
                    data={
                        "id": image_id,
                        "type": "delta",
                        "base_id": best_match["id"],
                        "similarity": best_ssim,
                        "savings_ratio": savings_ratio,
                    },
                    metadata={"message": f"Image stored as delta (saved {savings_ratio:.1%})"},
                )
        base_path = core.save_base_image(image_path, image_id)
        record = ImageRecord(
            id=image_id,
            phash=phash,
            original_path=str(Path(image_path).resolve()),
            is_base=True,
            width=width,
            height=height,
            file_size=original_size,
        )
        core.add_image_record(record)
        return ToolResult(
            success=True,
            data={"id": image_id, "type": "base", "path": base_path},
            metadata={"message": "Image added as base (no similar images found)"},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def remove_image(image_id: str, gallery_path: str = ".") -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        record = core.get_image_record(image_id)
        if not record:
            return ToolResult(success=False, error=f"Image not found: {image_id}")
        conn = core._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM images WHERE base_id = ? AND id != ?",
            (image_id, image_id),
        )
        dependent_count = cursor.fetchone()[0]
        if dependent_count > 0:
            return ToolResult(
                success=False,
                error=f"Cannot remove: {dependent_count} images depend on this base image",
            )
        core.delete_image_record(image_id)
        return ToolResult(
            success=True,
            data={"id": image_id},
            metadata={"message": "Image removed successfully"},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def get_image_info(image_id: str, gallery_path: str = ".") -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        record = core.get_image_record(image_id)
        if not record:
            return ToolResult(success=False, error=f"Image not found: {image_id}")
        return ToolResult(success=True, data=record)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def list_images(gallery_path: str = ".", limit: int = 100, offset: int = 0) -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        images = core.list_all_images()
        paginated = images[offset : offset + limit]
        return ToolResult(
            success=True,
            data={"images": paginated, "total": len(images), "limit": limit, "offset": offset},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def export_image(image_id: str, output_path: str, gallery_path: str = ".") -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        success = core.export_image(image_id, output_path)
        if success:
            return ToolResult(
                success=True,
                data={"output_path": output_path},
                metadata={"message": "Image exported successfully"},
            )
        return ToolResult(success=False, error="Failed to export image")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def find_similar(image_path: str, gallery_path: str = ".", threshold: int = 10) -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        if not Path(image_path).exists():
            return ToolResult(success=False, error=f"Image not found: {image_path}")
        phash = core.compute_hash(image_path)
        similar = core.find_similar_images(phash, threshold)
        return ToolResult(success=True, data={"phash": phash, "similar_images": similar})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def get_gallery_stats(gallery_path: str = ".") -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        stats = core.get_gallery_stats()
        return ToolResult(success=True, data=stats)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def set_config(
    gallery_path: str = ".",
    similarity_threshold: Optional[float] = None,
    min_delta_ratio: Optional[float] = None,
    max_hamming_distance: Optional[int] = None,
) -> ToolResult:
    try:
        core = KanTuCore(gallery_path)
        if not core.is_initialized():
            return ToolResult(success=False, error="Gallery not initialized")
        core._load_config()
        changes = {}
        if similarity_threshold is not None:
            core.config.similarity_threshold = similarity_threshold
            changes["similarity_threshold"] = similarity_threshold
        if min_delta_ratio is not None:
            core.config.min_delta_ratio = min_delta_ratio
            changes["min_delta_ratio"] = min_delta_ratio
        if max_hamming_distance is not None:
            core.config.max_hamming_distance = max_hamming_distance
            changes["max_hamming_distance"] = max_hamming_distance
        core._save_config()
        return ToolResult(
            success=True,
            data={"changes": changes},
            metadata={"message": "Configuration updated"},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))
