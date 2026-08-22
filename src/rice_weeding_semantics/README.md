# rice_weeding_semantics

Phase 4 semantic map contract package.

This package is a rice-field-specific implementation. It references the
project-owned semantic data-tool design in
`agt_navigation_v2-main/src/agt_ui_bridge/agt_ui_bridge`, but it does not
directly migrate AGT tools in this step. Direct migration is reserved for
standalone, plug-in-like modules only. It does not migrate the Qt editor, the
AGT semantic map server, Nav2 keepout filter launch files, coverage planning
code or any third-party algorithm.

Current contents:

- `semantic_model.py`: GeoJSON FeatureCollection data model.
- `semantic_io.py`: atomic JSON/YAML file loading and saving.
- `semantic_validation.py`: rice-field semantic schema checks.
- `profile_semantic_builder.py`: builds a simulation-only semantic map from
  `profiles/environments/paddy_field.yaml`.
- `semantic_mask.py`: pure-data keepout mask generation for hard obstacles,
  negative obstacles and keepout zones only.
- `generate_profile_semantic_map.py`: offline command-line generator that reads
  a paddy environment profile and writes GeoJSON.
- `generate_keepout_mask.py`: offline command-line exporter that writes a
  simulation-only `.pgm + .yaml` keepout-mask artifact from semantic GeoJSON.
- `semantic_keepout_mask_publisher.py`: guarded simulation-only
  `nav_msgs/OccupancyGrid` publisher for RViz and future Nav2 keepout contract
  checks. It requires `--acknowledge-simulation-only` and does not launch Nav2.
- `semantic_marker_preview.py`: read-only RViz MarkerArray preview for a
  semantic GeoJSON file. It publishes markers only, not masks, costmaps, TF or
  velocity.
- `config/rice_semantic_schema.yaml`: Phase 4 feature types and policies.
- `examples/paddy_demo/semantic_map.geojson`: versioned paddy demo map.

The base `/map` OccupancyGrid remains separate from semantic files. Rice plants
and weeds are semantic objects, not default Nav2 obstacles.

Example:

```bash
ros2 run rice_weeding_semantics generate_profile_semantic_map.py \
  --environment-profile profiles/environments/paddy_field.yaml \
  --output /tmp/paddy_semantic_map.geojson
```

Preview in RViz:

```bash
ros2 run rice_weeding_semantics semantic_marker_preview.py \
  --semantic-map /tmp/paddy_semantic_map.geojson
```

Generate a simulation-only keepout-mask artifact:

```bash
ros2 run rice_weeding_semantics generate_keepout_mask.py \
  --semantic-map /tmp/paddy_semantic_map.geojson \
  --output-yaml /tmp/paddy_keepout_mask.yaml \
  --resolution 0.1
```

Publish the same keepout mask online for RViz inspection:

```bash
ros2 run rice_weeding_semantics semantic_keepout_mask_publisher.py \
  --semantic-map /tmp/paddy_semantic_map.geojson \
  --resolution 0.1 \
  --acknowledge-simulation-only
```
