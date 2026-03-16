"""Command-line interface for KanTu."""

import argparse
import json
import sys

from kantu import __version__
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


def print_result(result: ToolResult, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    elif result.success:
        if result.data:
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    if key == "images":
                        continue
                    print(f"{key}: {value}")
            else:
                print(result.data)
        if result.metadata.get("message"):
            print(result.metadata["message"])
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def cmd_init(args: argparse.Namespace) -> None:
    result = init_gallery(args.path)
    print_result(result, getattr(args, "json_output", False))


def cmd_add(args: argparse.Namespace) -> None:
    for image_path in args.images:
        result = add_image(
            image_path=image_path,
            gallery_path=args.gallery,
            similarity_threshold=args.threshold,
            force_base=args.force_base,
        )
        print(f"\n{image_path}:")
        print_result(result, getattr(args, "json_output", False))


def cmd_remove(args: argparse.Namespace) -> None:
    result = remove_image(args.image_id, args.gallery)
    print_result(result, getattr(args, "json_output", False))


def cmd_info(args: argparse.Namespace) -> None:
    result = get_image_info(args.image_id, args.gallery)
    print_result(result, getattr(args, "json_output", False))


def cmd_list(args: argparse.Namespace) -> None:
    result = list_images(args.gallery, args.limit, args.offset)
    json_output = getattr(args, "json_output", False)
    if json_output:
        print_result(result, json_output)
    elif result.success:
        images = result.data.get("images", [])
        print(f"Total images: {result.data.get('total', 0)}")
        print("-" * 60)
        for img in images:
            img_type = "base" if img["is_base"] else "delta"
            print(
                f"ID: {img['id'][:12]}... | Type: {img_type} | Size: {img['width']}x{img['height']}"
            )
            if not img["is_base"] and img.get("base_id"):
                print(
                    f"  Base: {img['base_id'][:12]}... | Similarity: {img.get('similarity_score', 0):.2%}"
                )


def cmd_export(args: argparse.Namespace) -> None:
    result = export_image(args.image_id, args.output, args.gallery)
    print_result(result, getattr(args, "json_output", False))


def cmd_similar(args: argparse.Namespace) -> None:
    result = find_similar(args.image, args.gallery, args.threshold)
    json_output = getattr(args, "json_output", False)
    if json_output:
        print_result(result, json_output)
    elif result.success:
        print(f"Image hash: {result.data.get('phash')}")
        similar = result.data.get("similar_images", [])
        if similar:
            print(f"\nFound {len(similar)} similar images:")
            for img in similar:
                print(f"  {img['id'][:12]}... | Distance: {img['distance']}")
        else:
            print("No similar images found.")


def cmd_stats(args: argparse.Namespace) -> None:
    result = get_gallery_stats(args.gallery)
    json_output = getattr(args, "json_output", False)
    if json_output:
        print_result(result, json_output)
    elif result.success:
        stats = result.data
        print("Gallery Statistics")
        print("=" * 40)
        print(f"Total images:    {stats['total_images']}")
        print(f"Base images:     {stats['base_images']}")
        print(f"Delta images:    {stats['delta_images']}")
        print("-" * 40)
        print(f"Base size:       {_format_size(stats['base_size'])}")
        print(f"Delta size:      {_format_size(stats['delta_size'])}")
        print(f"Total size:      {_format_size(stats['total_size'])}")
        print("-" * 40)
        print(f"Original size:   {_format_size(stats['original_size'])}")
        print(f"Storage saved:   {stats['savings_ratio']:.1%}")


def cmd_config(args: argparse.Namespace) -> None:
    kwargs = {}
    if args.similarity_threshold is not None:
        kwargs["similarity_threshold"] = args.similarity_threshold
    if args.min_delta_ratio is not None:
        kwargs["min_delta_ratio"] = args.min_delta_ratio
    if args.max_hamming_distance is not None:
        kwargs["max_hamming_distance"] = args.max_hamming_distance
    result = set_config(args.gallery, **kwargs)
    print_result(result, args.json)


def cmd_gui(args: argparse.Namespace) -> None:
    from kantu.gui import run_gui

    run_gui(args.gallery, args.no_web)


def cmd_web(args: argparse.Namespace) -> None:
    from kantu.app import run_server

    run_server(host=args.host, port=args.port, gallery_path=args.gallery)


def _format_size(size: int) -> str:
    s = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if s < 1024:
            return f"{s:.2f} {unit}"
        s /= 1024
    return f"{s:.2f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kantu",
        description="Git-like image gallery management with delta encoding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"kantu {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    init_parser = subparsers.add_parser("init", help="Initialize a new gallery")
    init_parser.add_argument("path", nargs="?", default=".", help="Gallery path")
    init_parser.set_defaults(func=cmd_init)
    add_parser = subparsers.add_parser("add", help="Add images to gallery")
    add_parser.add_argument("images", nargs="+", help="Image files to add")
    add_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    add_parser.add_argument("-t", "--threshold", type=float, help="Similarity threshold (0-1)")
    add_parser.add_argument("--force-base", action="store_true", help="Force store as base image")
    add_parser.set_defaults(func=cmd_add)
    remove_parser = subparsers.add_parser(
        "remove", aliases=["rm"], help="Remove image from gallery"
    )
    remove_parser.add_argument("image_id", help="Image ID to remove")
    remove_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    remove_parser.set_defaults(func=cmd_remove)
    info_parser = subparsers.add_parser("info", help="Get image information")
    info_parser.add_argument("image_id", help="Image ID")
    info_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    info_parser.set_defaults(func=cmd_info)
    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List images in gallery")
    list_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    list_parser.add_argument("-l", "--limit", type=int, default=100, help="Limit results")
    list_parser.add_argument("-o", "--offset", type=int, default=0, help="Offset results")
    list_parser.set_defaults(func=cmd_list)
    export_parser = subparsers.add_parser("export", help="Export image from gallery")
    export_parser.add_argument("image_id", help="Image ID to export")
    export_parser.add_argument("-o", "--output", required=True, help="Output file path")
    export_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    export_parser.set_defaults(func=cmd_export)
    similar_parser = subparsers.add_parser("similar", help="Find similar images")
    similar_parser.add_argument("image", help="Image file to compare")
    similar_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    similar_parser.add_argument(
        "-t", "--threshold", type=int, default=10, help="Hamming distance threshold"
    )
    similar_parser.set_defaults(func=cmd_similar)
    stats_parser = subparsers.add_parser("stats", help="Show gallery statistics")
    stats_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    stats_parser.set_defaults(func=cmd_stats)
    config_parser = subparsers.add_parser("config", help="Configure gallery settings")
    config_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    config_parser.add_argument(
        "--similarity-threshold", type=float, help="Similarity threshold (0-1)"
    )
    config_parser.add_argument(
        "--min-delta-ratio", type=float, help="Minimum delta ratio to store as delta"
    )
    config_parser.add_argument(
        "--max-hamming-distance", type=int, help="Maximum hamming distance for similarity"
    )
    config_parser.set_defaults(func=cmd_config)
    gui_parser = subparsers.add_parser("gui", help="Launch GUI")
    gui_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    gui_parser.add_argument("--no-web", action="store_true", help="Disable embedded web server")
    gui_parser.set_defaults(func=cmd_gui)
    web_parser = subparsers.add_parser("web", help="Launch web server")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host address")
    web_parser.add_argument("--port", type=int, default=5000, help="Port number")
    web_parser.add_argument("-g", "--gallery", default=".", help="Gallery path")
    web_parser.set_defaults(func=cmd_web)
    args = parser.parse_args()
    if args.command is None:
        from kantu.gui import run_gui

        run_gui(".", False)
        return 0
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
