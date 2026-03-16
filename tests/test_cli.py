"""Tests for KanTu CLI."""

import subprocess
import sys
from pathlib import Path


class TestCLI:
    def test_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "kantu", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "kantu" in result.stdout

    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "kantu", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "init" in result.stdout
        assert "add" in result.stdout
        assert "list" in result.stdout

    def test_init(self, temp_gallery):
        result = subprocess.run(
            [sys.executable, "-m", "kantu", "init", temp_gallery],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert (Path(temp_gallery) / ".kantu").exists()

    def test_list_empty(self, temp_gallery):
        subprocess.run(
            [sys.executable, "-m", "kantu", "init", temp_gallery],
            capture_output=True,
        )
        result = subprocess.run(
            [sys.executable, "-m", "kantu", "list", "-g", temp_gallery],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Total images: 0" in result.stdout

    def test_stats(self, temp_gallery):
        subprocess.run(
            [sys.executable, "-m", "kantu", "init", temp_gallery],
            capture_output=True,
        )
        result = subprocess.run(
            [sys.executable, "-m", "kantu", "stats", "-g", temp_gallery],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Gallery Statistics" in result.stdout
