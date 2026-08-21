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
- `config/rice_semantic_schema.yaml`: Phase 4 feature types and policies.
- `examples/paddy_demo/semantic_map.geojson`: versioned paddy demo map.

The base `/map` OccupancyGrid remains separate from semantic files. Rice plants
and weeds are semantic objects, not default Nav2 obstacles.
