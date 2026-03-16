"""Test configuration and fixtures for KanTu."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def temp_gallery():
    """Create a temporary gallery directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_images(temp_gallery):
    """Create sample test images."""
    images_dir = Path(temp_gallery) / "images"
    images_dir.mkdir()
    base_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    base_path = images_dir / "base.png"
    Image.fromarray(base_img).save(base_path)
    similar_img = base_img.copy()
    similar_img[10:20, 10:20] = 255 - similar_img[10:20, 10:20]
    similar_path = images_dir / "similar.png"
    Image.fromarray(similar_img).save(similar_path)
    diff_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    diff_path = images_dir / "different.png"
    Image.fromarray(diff_img).save(diff_path)
    return {
        "base": str(base_path),
        "similar": str(similar_path),
        "different": str(diff_path),
        "dir": str(images_dir),
    }


@pytest.fixture
def initialized_gallery(temp_gallery, sample_images):
    """Create an initialized gallery with one base image."""
    from kantu.api import add_image, init_gallery

    init_gallery(temp_gallery)
    add_image(sample_images["base"], temp_gallery, force_base=True)
    return temp_gallery
