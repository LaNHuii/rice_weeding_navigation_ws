#!/usr/bin/python3
"""Generate a simulation-only keepout mask from rice semantic GeoJSON."""

import argparse
from pathlib import Path
import sys

try:
    from ament_index_python.packages import get_package_share_directory
except ImportError:
    get_package_share_directory = None


def _add_package_to_path():
    if get_package_share_directory is not None:
        module_path = Path(get_package_share_directory("rice_weeding_semantics"))
    else:
        module_path = Path(__file__).resolve().parents[1]
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))


_add_package_to_path()

from rice_weeding_semantics.semantic_io import load_semantic_map
from rice_weeding_semantics.semantic_mask import (
    build_keepout_mask,
    geometry_from_semantic_bounds,
    save_keepout_mask_files,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a pure-data keepout mask from semantic GeoJSON."
    )
    parser.add_argument("--semantic-map", required=True)
    parser.add_argument("--output-yaml", required=True)
    parser.add_argument("--resolution", type=float, default=0.1)
    parser.add_argument("--padding", type=float, default=0.0)
    args = parser.parse_args()

    semantic_map = load_semantic_map(args.semantic_map)
    geometry = geometry_from_semantic_bounds(
        semantic_map,
        resolution=args.resolution,
        padding=args.padding,
    )
    mask = build_keepout_mask(semantic_map, geometry)
    save_keepout_mask_files(mask, args.output_yaml)
    print(
        "Generated keepout mask: "
        f"{args.output_yaml} "
        f"({mask.width}x{mask.height}, occupied={mask.occupied_count})"
    )


if __name__ == "__main__":
    main()
