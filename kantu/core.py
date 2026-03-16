"""Core functionality for KanTu: image hashing, similarity detection, and delta encoding."""

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import imagehash
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim


class DeltaType(Enum):
    NONE = "none"
    PIXEL = "pixel"
    TRANSFORM = "transform"


@dataclass
class ImageRecord:
    id: str
    phash: str
    original_path: str
    is_base: bool
    base_id: Optional[str] = None
    delta_type: DeltaType = DeltaType.NONE
    delta_path: Optional[str] = None
    width: int = 0
    height: int = 0
    file_size: int = 0
    similarity_score: float = 1.0


@dataclass
class GalleryConfig:
    similarity_threshold: float = 0.85
    min_delta_ratio: float = 0.5
    hash_size: int = 16
    max_hamming_distance: int = 10


class KanTuCore:
    KANTU_DIR = ".kantu"
    OBJECTS_DIR = "objects"
    BASE_DIR = "base"
    DELTA_DIR = "delta"
    DB_FILE = "gallery.db"
    CONFIG_FILE = "config.json"

    def __init__(self, gallery_path: str):
        self.gallery_path = Path(gallery_path).resolve()
        self.kantu_path = self.gallery_path / self.KANTU_DIR
        self.objects_path = self.kantu_path / self.OBJECTS_DIR
        self.base_path = self.objects_path / self.BASE_DIR
        self.delta_path = self.objects_path / self.DELTA_DIR
        self.db_path = self.kantu_path / self.DB_FILE
        self.config_path = self.kantu_path / self.CONFIG_FILE
        self.config = GalleryConfig()
        self._conn: Optional[sqlite3.Connection] = None

    def is_initialized(self) -> bool:
        return self.kantu_path.exists() and self.db_path.exists()

    def init_gallery(self) -> bool:
        if self.is_initialized():
            return True
        self.kantu_path.mkdir(parents=True, exist_ok=True)
        self.objects_path.mkdir(parents=True, exist_ok=True)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.delta_path.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._save_config()
        return True

    def _init_database(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                phash TEXT NOT NULL,
                original_path TEXT,
                is_base INTEGER NOT NULL,
                base_id TEXT,
                delta_type TEXT DEFAULT 'none',
                delta_path TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_phash ON images(phash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_base_id ON images(base_id)
        """)
        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _save_config(self) -> None:
        config_data = {
            "similarity_threshold": self.config.similarity_threshold,
            "min_delta_ratio": self.config.min_delta_ratio,
            "hash_size": self.config.hash_size,
            "max_hamming_distance": self.config.max_hamming_distance,
        }
        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=2)

    def _load_config(self) -> None:
        if self.config_path.exists():
            with open(self.config_path) as f:
                config_data = json.load(f)
            self.config.similarity_threshold = config_data.get("similarity_threshold", 0.85)
            self.config.min_delta_ratio = config_data.get("min_delta_ratio", 0.5)
            self.config.hash_size = config_data.get("hash_size", 16)
            self.config.max_hamming_distance = config_data.get("max_hamming_distance", 10)

    def compute_hash(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img_hash = imagehash.phash(img, hash_size=self.config.hash_size)
            return str(img_hash)

    def compute_id(self, image_path: str) -> str:
        hasher = hashlib.sha256()
        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]

    def compute_ssim(self, img1_path: str, img2_path: str) -> float:
        with Image.open(img1_path) as img1:
            if img1.mode != "RGB":
                img1 = img1.convert("RGB")
            arr1 = np.array(img1)
        with Image.open(img2_path) as img2:
            if img2.mode != "RGB":
                img2 = img2.convert("RGB")
            arr2 = np.array(img2)
        min_h = min(arr1.shape[0], arr2.shape[0])
        min_w = min(arr1.shape[1], arr2.shape[1])
        arr1 = arr1[:min_h, :min_w]
        arr2 = arr2[:min_h, :min_w]
        if arr1.shape[2] == 3:
            scores = []
            for i in range(3):
                score = ssim(arr1[:, :, i], arr2[:, :, i], data_range=255)
                scores.append(score)
            return float(np.mean(scores))
        else:
            return float(ssim(arr1, arr2, data_range=255))

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)

    def find_similar_images(self, phash: str, threshold: Optional[int] = None) -> list[dict]:
        if threshold is None:
            threshold = self.config.max_hamming_distance
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE is_base = 1")
        candidates = []
        for row in cursor.fetchall():
            stored_hash = row["phash"]
            distance = self.hamming_distance(phash, stored_hash)
            if distance <= threshold:
                candidates.append(
                    {
                        "id": row["id"],
                        "phash": stored_hash,
                        "distance": distance,
                        "original_path": row["original_path"],
                    }
                )
        candidates.sort(key=lambda x: x["distance"])
        return candidates

    def compute_pixel_delta(
        self, img1_path: str, img2_path: str
    ) -> tuple[np.ndarray, tuple[int, int]]:
        with Image.open(img1_path) as img1:
            if img1.mode != "RGB":
                img1 = img1.convert("RGB")
            arr1 = np.array(img1, dtype=np.int16)
        with Image.open(img2_path) as img2:
            if img2.mode != "RGB":
                img2 = img2.convert("RGB")
            arr2 = np.array(img2, dtype=np.int16)
        max_h = max(arr1.shape[0], arr2.shape[0])
        max_w = max(arr1.shape[1], arr2.shape[1])
        padded1 = np.zeros((max_h, max_w, 3), dtype=np.int16)
        padded2 = np.zeros((max_h, max_w, 3), dtype=np.int16)
        padded1[: arr1.shape[0], : arr1.shape[1]] = arr1
        padded2[: arr2.shape[0], : arr2.shape[1]] = arr2
        delta = padded2 - padded1
        return delta.astype(np.int16), (arr2.shape[0], arr2.shape[1])

    def apply_pixel_delta(
        self, base_path: str, delta: np.ndarray, target_size: tuple[int, int]
    ) -> np.ndarray:
        with Image.open(base_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            base_arr = np.array(img, dtype=np.int16)
        max_h = max(base_arr.shape[0], delta.shape[0])
        max_w = max(base_arr.shape[1], delta.shape[1])
        padded_base = np.zeros((max_h, max_w, 3), dtype=np.int16)
        padded_base[: base_arr.shape[0], : base_arr.shape[1]] = base_arr
        result = padded_base + delta
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result[: target_size[0], : target_size[1]]

    def save_delta(self, delta: np.ndarray, delta_id: str) -> str:
        delta_file = self.delta_path / f"{delta_id}.npy"
        np.save(str(delta_file), delta)
        return str(delta_file)

    def load_delta(self, delta_id: str) -> np.ndarray:
        delta_file = self.delta_path / f"{delta_id}.npy"
        return np.load(str(delta_file))

    def save_base_image(self, image_path: str, image_id: str) -> str:
        ext = Path(image_path).suffix.lower()
        if ext in [".jpg", ".jpeg"]:
            ext = ".jpg"
        elif ext == ".png":
            ext = ".png"
        else:
            ext = ".jpg"
        base_file = self.base_path / f"{image_id}{ext}"
        with Image.open(image_path) as img:
            img.save(base_file, quality=95 if ext == ".jpg" else None)
        return str(base_file)

    def get_image_dimensions(self, image_path: str) -> tuple[int, int]:
        with Image.open(image_path) as img:
            return img.size

    def get_file_size(self, path: str) -> int:
        return os.path.getsize(path)

    def add_image_record(self, record: ImageRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO images
            (id, phash, original_path, is_base, base_id, delta_type,
             delta_path, width, height, file_size, similarity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.phash,
                record.original_path,
                1 if record.is_base else 0,
                record.base_id,
                record.delta_type.value,
                record.delta_path,
                record.width,
                record.height,
                record.file_size,
                record.similarity_score,
            ),
        )
        conn.commit()

    def get_image_record(self, image_id: str) -> Optional[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_all_images(self) -> list[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def delete_image_record(self, image_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if not row:
            return False
        delta_path = row["delta_path"]
        if delta_path and os.path.exists(delta_path):
            os.remove(delta_path)
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        conn.commit()
        return True

    def get_gallery_stats(self) -> dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM images")
        total_images = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM images WHERE is_base = 1")
        base_images = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM images WHERE is_base = 0")
        delta_images = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(file_size) FROM images WHERE is_base = 1")
        base_size = cursor.fetchone()[0] or 0
        cursor.execute(
            "SELECT SUM(file_size) FROM images WHERE is_base = 0 AND delta_path IS NOT NULL"
        )
        delta_size = cursor.fetchone()[0] or 0
        cursor.execute("SELECT original_path, file_size FROM images WHERE is_base = 0")
        original_total = 0
        for row in cursor.fetchall():
            if row["original_path"] and os.path.exists(row["original_path"]):
                original_total += os.path.getsize(row["original_path"])
        savings = 0
        if original_total > 0:
            savings = 1 - (base_size + delta_size) / original_total
        return {
            "total_images": total_images,
            "base_images": base_images,
            "delta_images": delta_images,
            "base_size": base_size,
            "delta_size": delta_size,
            "total_size": base_size + delta_size,
            "original_size": original_total,
            "savings_ratio": savings,
        }

    def reconstruct_image(self, image_id: str) -> Optional[np.ndarray]:
        record = self.get_image_record(image_id)
        if not record:
            return None
        if record["is_base"]:
            base_path = self.base_path / f"{image_id}.*"
            import glob

            matches = glob.glob(str(base_path))
            if matches:
                with Image.open(matches[0]) as img:
                    return np.array(img)
            return None
        base_id = record["base_id"]
        if not base_id:
            return None
        base_record = self.get_image_record(base_id)
        if not base_record:
            return None
        base_pattern = str(self.base_path / f"{base_id}.*")
        import glob

        matches = glob.glob(base_pattern)
        if not matches:
            return None
        delta_id = Path(record["delta_path"]).stem if record["delta_path"] else image_id
        delta = self.load_delta(delta_id)
        target_size = (record["height"], record["width"])
        return self.apply_pixel_delta(matches[0], delta, target_size)

    def export_image(self, image_id: str, output_path: str) -> bool:
        arr = self.reconstruct_image(image_id)
        if arr is None:
            return False
        img = Image.fromarray(arr)
        img.save(output_path)
        return True

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
