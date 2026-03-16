"""KanTu - Git-like image gallery management with delta encoding."""

__version__ = "1.0.0"
__author__ = "KanTu Developers"

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
)

__all__ = [
    "ToolResult",
    "init_gallery",
    "add_image",
    "remove_image",
    "get_image_info",
    "list_images",
    "export_image",
    "find_similar",
    "get_gallery_stats",
    "__version__",
]
