#!/usr/bin/python3
"""Generate a simulation-only rice semantic map from an environment profile."""

import argparse
from pathlib import Path
import sys

import yaml

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

from rice_weeding_semantics.profile_semantic_builder import build_paddy_semantic_map
from rice_weeding_semantics.semantic_io import save_semantic_map
from rice_weeding_semantics.semantic_validation import validate_semantic_map


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Phase 4 semantic GeoJSON from paddy_field.yaml."
    )
    parser.add_argument("--environment-profile", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--map-id", default="paddy_profile_demo")
    args = parser.parse_args()

    profile_path = Path(args.environment_profile)
    output_path = Path(args.output)
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    semantic_map = build_paddy_semantic_map(profile, map_id=args.map_id)
    report = validate_semantic_map(semantic_map)
    if not report.valid:
        for issue in report.issues:
            print(f"{issue.severity} {issue.code} {issue.object_id}: {issue.message}", file=sys.stderr)
        return 1
    save_semantic_map(semantic_map, output_path)
    print(f"Generated semantic map: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
