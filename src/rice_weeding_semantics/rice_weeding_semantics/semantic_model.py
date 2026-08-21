"""Serializable rice-field semantic map data models."""

from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class SemanticFeature:
    id: str
    feature_type: str
    name: str
    geometry_type: str
    coordinates: object
    enabled: bool = True
    frame_id: str = "map"
    properties: dict = field(default_factory=dict)

    @classmethod
    def from_geojson(cls, feature):
        properties = deepcopy(feature.get("properties", {}))
        known = {
            key: properties.pop(key)
            for key in ("id", "feature_type", "name")
            if key in properties
        }
        enabled = properties.pop("enabled", True)
        frame_id = properties.pop("frame_id", "map")
        geometry = feature.get("geometry", {})
        return cls(
            id=known.get("id", ""),
            feature_type=known.get("feature_type", ""),
            name=known.get("name", ""),
            geometry_type=geometry.get("type", ""),
            coordinates=deepcopy(geometry.get("coordinates")),
            enabled=enabled,
            frame_id=frame_id,
            properties=properties,
        )

    def to_geojson(self):
        properties = deepcopy(self.properties)
        properties.update({
            "id": self.id,
            "feature_type": self.feature_type,
            "name": self.name,
            "enabled": self.enabled,
            "frame_id": self.frame_id,
        })
        return {
            "type": "Feature",
            "geometry": {
                "type": self.geometry_type,
                "coordinates": deepcopy(self.coordinates),
            },
            "properties": properties,
        }


@dataclass
class SemanticMap:
    map_id: str
    features: list = field(default_factory=list)
    schema_version: str = "1.0"
    frame_id: str = "map"

    @classmethod
    def from_geojson(cls, document):
        if document.get("type") != "FeatureCollection":
            raise ValueError("semantic map must be a GeoJSON FeatureCollection")
        return cls(
            schema_version=str(document.get("schema_version", "")),
            map_id=str(document.get("map_id", "")),
            frame_id=str(document.get("frame_id", "")),
            features=[
                SemanticFeature.from_geojson(feature)
                for feature in document.get("features", [])
            ],
        )

    def to_geojson(self):
        return {
            "type": "FeatureCollection",
            "schema_version": self.schema_version,
            "map_id": self.map_id,
            "frame_id": self.frame_id,
            "features": [feature.to_geojson() for feature in self.features],
        }
