"""Tests for KanTu API functions."""

from kantu.api import (
    ToolResult,
    add_image,
    export_image,
    find_similar,
    get_gallery_stats,
    get_image_info,
    init_gallery,
    list_images,
    remove_image,
    set_config,
)


class TestToolResult:
    def test_success_result(self):
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_error_result(self):
        result = ToolResult(success=False, error="Something went wrong")
        assert not result.success
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        result = ToolResult(
            success=True,
            data={"id": 123},
            metadata={"message": "Done"},
        )
        d = result.to_dict()
        assert d["success"]
        assert d["data"]["id"] == 123
        assert d["metadata"]["message"] == "Done"


class TestInitGallery:
    def test_init_new_gallery(self, temp_gallery):
        result = init_gallery(temp_gallery)
        assert result.success
        assert "path" in result.data

    def test_init_existing_gallery(self, temp_gallery):
        init_gallery(temp_gallery)
        result = init_gallery(temp_gallery)
        assert result.success
        assert "already initialized" in result.metadata.get("message", "")


class TestAddImage:
    def test_add_base_image(self, temp_gallery, sample_images):
        init_gallery(temp_gallery)
        result = add_image(sample_images["base"], temp_gallery, force_base=True)
        assert result.success
        assert result.data["type"] == "base"

    def test_add_duplicate_image(self, temp_gallery, sample_images):
        init_gallery(temp_gallery)
        add_image(sample_images["base"], temp_gallery, force_base=True)
        result = add_image(sample_images["base"], temp_gallery)
        assert result.success
        assert result.data["status"] == "already_exists"

    def test_add_without_init(self, temp_gallery, sample_images):
        result = add_image(sample_images["base"], temp_gallery)
        assert not result.success
        assert "not initialized" in result.error

    def test_add_nonexistent_image(self, temp_gallery):
        init_gallery(temp_gallery)
        result = add_image("/nonexistent/image.png", temp_gallery)
        assert not result.success
        assert "not found" in result.error


class TestRemoveImage:
    def test_remove_image(self, initialized_gallery, sample_images):
        from kantu.api import add_image, get_image_info

        result = add_image(sample_images["similar"], initialized_gallery)
        image_id = result.data["id"]
        remove_result = remove_image(image_id, initialized_gallery)
        assert remove_result.success
        info = get_image_info(image_id, initialized_gallery)
        assert not info.success

    def test_remove_nonexistent(self, initialized_gallery):
        result = remove_image("nonexistent123", initialized_gallery)
        assert not result.success


class TestGetImageInfo:
    def test_get_info(self, initialized_gallery):
        images = list_images(initialized_gallery)
        if images.success and images.data["images"]:
            image_id = images.data["images"][0]["id"]
            info = get_image_info(image_id, initialized_gallery)
            assert info.success
            assert info.data["id"] == image_id

    def test_get_info_nonexistent(self, initialized_gallery):
        result = get_image_info("nonexistent", initialized_gallery)
        assert not result.success


class TestListImages:
    def test_list_empty(self, temp_gallery):
        init_gallery(temp_gallery)
        result = list_images(temp_gallery)
        assert result.success
        assert result.data["total"] == 0

    def test_list_with_images(self, initialized_gallery):
        result = list_images(initialized_gallery)
        assert result.success
        assert result.data["total"] >= 1

    def test_list_pagination(self, initialized_gallery):
        result = list_images(initialized_gallery, limit=1, offset=0)
        assert result.success
        assert len(result.data["images"]) <= 1


class TestExportImage:
    def test_export_image(self, initialized_gallery, temp_gallery):
        import os

        images = list_images(initialized_gallery)
        if images.success and images.data["images"]:
            image_id = images.data["images"][0]["id"]
            output_path = os.path.join(temp_gallery, "exported.png")
            result = export_image(image_id, output_path, initialized_gallery)
            assert result.success
            assert os.path.exists(output_path)


class TestFindSimilar:
    def test_find_similar(self, initialized_gallery, sample_images):
        result = find_similar(sample_images["similar"], initialized_gallery)
        assert result.success
        assert "phash" in result.data
        assert "similar_images" in result.data


class TestGetGalleryStats:
    def test_stats(self, initialized_gallery):
        result = get_gallery_stats(initialized_gallery)
        assert result.success
        assert "total_images" in result.data
        assert "base_images" in result.data
        assert "delta_images" in result.data


class TestSetConfig:
    def test_set_config(self, initialized_gallery):
        result = set_config(
            initialized_gallery,
            similarity_threshold=0.9,
            min_delta_ratio=0.3,
        )
        assert result.success
        assert "similarity_threshold" in result.data["changes"]
