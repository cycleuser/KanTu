"""Tests for KanTu core functionality."""

from pathlib import Path

from kantu.core import ImageRecord, KanTuCore


class TestKanTuCore:
    def test_init_gallery(self, temp_gallery):
        core = KanTuCore(temp_gallery)
        assert not core.is_initialized()
        core.init_gallery()
        assert core.is_initialized()
        assert core.kantu_path.exists()
        assert core.db_path.exists()

    def test_compute_hash(self, temp_gallery, sample_images):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        hash1 = core.compute_hash(sample_images["base"])
        hash2 = core.compute_hash(sample_images["similar"])
        assert isinstance(hash1, str)
        assert len(hash1) == 64
        distance = core.hamming_distance(hash1, hash2)
        assert distance <= 25

    def test_compute_id(self, temp_gallery, sample_images):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        id1 = core.compute_id(sample_images["base"])
        id2 = core.compute_id(sample_images["similar"])
        assert isinstance(id1, str)
        assert len(id1) == 16
        assert id1 != id2

    def test_compute_ssim(self, temp_gallery, sample_images):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        ssim_score = core.compute_ssim(sample_images["base"], sample_images["similar"])
        assert 0 <= ssim_score <= 1
        assert ssim_score > 0.9
        ssim_diff = core.compute_ssim(sample_images["base"], sample_images["different"])
        assert ssim_diff < ssim_score

    def test_hamming_distance(self, temp_gallery):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        hash1 = "a" * 64
        hash2 = "a" * 63 + "b"
        distance = core.hamming_distance(hash1, hash2)
        assert isinstance(int(distance), int)
        assert distance >= 0

    def test_pixel_delta(self, temp_gallery, sample_images):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        delta, target_size = core.compute_pixel_delta(
            sample_images["base"], sample_images["similar"]
        )
        assert delta.shape == (100, 100, 3)
        assert target_size == (100, 100)

    def test_save_and_load_delta(self, temp_gallery, sample_images):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        import numpy as np

        delta = np.random.randint(-128, 127, (100, 100, 3), dtype=np.int16)
        delta_path = core.save_delta(delta, "test_delta")
        assert Path(delta_path).exists()
        loaded = core.load_delta("test_delta")
        np.testing.assert_array_equal(delta, loaded)

    def test_add_and_get_image_record(self, temp_gallery):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        record = ImageRecord(
            id="test123",
            phash="a" * 64,
            original_path="/test/image.png",
            is_base=True,
            width=100,
            height=100,
            file_size=1000,
        )
        core.add_image_record(record)
        retrieved = core.get_image_record("test123")
        assert retrieved is not None
        assert retrieved["id"] == "test123"
        assert retrieved["is_base"] == 1

    def test_list_all_images(self, temp_gallery):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        for i in range(3):
            record = ImageRecord(
                id=f"test{i}",
                phash=f"{i}" * 64,
                original_path=f"/test/image{i}.png",
                is_base=True,
                width=100,
                height=100,
                file_size=1000,
            )
            core.add_image_record(record)
        images = core.list_all_images()
        assert len(images) == 3

    def test_gallery_stats(self, temp_gallery):
        core = KanTuCore(temp_gallery)
        core.init_gallery()
        stats = core.get_gallery_stats()
        assert stats["total_images"] == 0
        assert stats["base_images"] == 0
        record = ImageRecord(
            id="test123",
            phash="a" * 64,
            original_path="/test/image.png",
            is_base=True,
            width=100,
            height=100,
            file_size=1000,
        )
        core.add_image_record(record)
        stats = core.get_gallery_stats()
        assert stats["total_images"] == 1
        assert stats["base_images"] == 1
