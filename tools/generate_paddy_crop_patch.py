#!/usr/bin/env python3
"""Regenerate the bounded field and visual-only crop mesh from its profile."""

from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles/environments/paddy_field.yaml"
WORLD = ROOT / "src/rice_weeding_simulation/worlds/paddy_field.sdf"
MESH = ROOT / "src/rice_weeding_simulation/meshes/paddy_crops.obj"
MATERIAL = ROOT / "src/rice_weeding_simulation/meshes/paddy_crops.mtl"
BOUNDARY_MESH = ROOT / "src/rice_weeding_simulation/meshes/paddy_boundary.obj"
BOUNDARY_MATERIAL = ROOT / "src/rice_weeding_simulation/meshes/paddy_boundary.mtl"


def element(parent, tag, text=None, **attributes):
    child = ET.SubElement(parent, tag, attributes)
    if text is not None:
        child.text = text
    return child


def main():
    environment = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))["environment"]
    field = environment["field"]
    bund = field["bund"]
    crop_grid = environment["crop_grid"]
    visual_model = crop_grid["visual_model"]

    if visual_model["verified"] is not False or visual_model["simulation_only"] is not True:
        raise ValueError("Provisional crop geometry must remain explicitly simulation-only")

    tree = ET.parse(WORLD)
    world = tree.getroot().find("world")
    for model in list(world.findall("model")):
        if (model.attrib["name"].startswith("crop_row_") or
                model.attrib["name"] in {"crop_field", "field_boundary"}):
            world.remove(model)

    outer_length = float(field["boundary_outer_length"])
    outer_width = float(field["boundary_outer_width"])
    bund_thickness = float(bund["thickness"])
    bund_height = float(bund["height"])
    bund_color = " ".join(str(value) for value in bund["color_rgba"])
    if abs(outer_length * outer_width - float(field["boundary_outer_area"])) > 1.0e-9:
        raise ValueError("Boundary dimensions must match boundary_outer_area")
    if abs(float(field["boundary_outer_area"]) * 2.0 -
           float(field["previous_boundary_outer_area"])) > 1.0e-9:
        raise ValueError("The revised field area must be exactly half of the previous area")
    if bund["visual_topology"] != "single_rectangular_frame":
        raise ValueError("The visible boundary must be one rectangular frame")

    inner_length = outer_length - 2.0 * bund_thickness
    inner_width = outer_width - 2.0 * bund_thickness
    row_spacing = float(crop_grid["row_spacing"])
    plant_spacing = float(crop_grid["plant_spacing"])
    headland_width = float(field["headland_width"])
    footprint_length = float(visual_model["footprint_length"])
    footprint_width = float(visual_model["footprint_width"])
    height = float(visual_model["height"])
    if crop_grid["row_direction_yaw"] != 0.0:
        raise ValueError("The current crop mesh generator supports rows along field length only")
    if field.get("headland_axis") != "field_length_ends":
        raise ValueError("Headlands must occupy both ends of the field length")
    crop_length = inner_length - 2.0 * headland_width
    if crop_length < footprint_length:
        raise ValueError("Headlands leave no room for crop plants")
    row_count = int((inner_width - footprint_width) / row_spacing) + 1
    plant_count = int((crop_length - footprint_length) / plant_spacing) + 1
    color = " ".join(str(value) for value in visual_model["color_rgba"])

    # Make the mud and water fit exactly inside the four bunds.
    mud = world.find("model[@name='mud_surface']")
    mud.find("link/collision/geometry/box/size").text = f"{inner_length:.3f} {inner_width:.3f} 0.10"
    mud.find("link/visual/geometry/box/size").text = f"{inner_length:.3f} {inner_width:.3f} 0.10"
    water = world.find("model[@name='shallow_water_visual']")
    water.find("link/visual/geometry/box/size").text = f"{inner_length:.3f} {inner_width:.3f} 0.01"

    half_length = outer_length / 2.0
    half_width = outer_width / 2.0
    collision_specs = {
        "north_bund": (0.0, half_width-bund_thickness/2.0,
                       outer_length, bund_thickness),
        "south_bund": (0.0, -half_width+bund_thickness/2.0,
                       outer_length, bund_thickness),
        "east_bund": (half_length-bund_thickness/2.0, 0.0,
                      bund_thickness, inner_width),
        "west_bund": (-half_length+bund_thickness/2.0, 0.0,
                      bund_thickness, inner_width),
    }
    for name, (x, y, length, width) in collision_specs.items():
        model = world.find(f"model[@name='{name}']")
        model.find("pose").text = f"{x:.3f} {y:.3f} {bund_height/2.0:.3f} 0 0 0"
        geometry = model.find("link/collision/geometry")
        for child in list(geometry):
            geometry.remove(child)
        box = element(geometry, "box")
        element(box, "size", f"{length:.3f} {width:.3f} {bund_height:.3f}")
        visual = model.find("link/visual")
        if visual is not None:
            model.find("link").remove(visual)

    # One OBJ keeps Gazebo responsive while every plant remains a disconnected cuboid.
    # Crops are centered in the remaining length, leaving symmetric end headlands.
    MESH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Generated from profiles/environments/paddy_field.yaml",
             "mtllib paddy_crops.mtl", "o paddy_crops", "usemtl rice_green",
             "vn 0 0 -1", "vn 0 0 1", "vn 0 -1 0", "vn 1 0 0",
             "vn 0 1 0", "vn -1 0 0"]
    vertex_offset = 1
    half_x = footprint_length / 2.0
    half_y = footprint_width / 2.0
    faces = ((1, 2, 3, 4), (5, 8, 7, 6), (1, 5, 6, 2),
             (2, 6, 7, 3), (3, 7, 8, 4), (5, 1, 4, 8))
    for row_index in range(row_count):
        y = (row_index - (row_count - 1) / 2.0) * row_spacing
        for plant_index in range(plant_count):
            x = (plant_index - (plant_count - 1) / 2.0) * plant_spacing
            vertices = ((x-half_x, y-half_y, 0.0), (x+half_x, y-half_y, 0.0),
                        (x+half_x, y+half_y, 0.0), (x-half_x, y+half_y, 0.0),
                        (x-half_x, y-half_y, height), (x+half_x, y-half_y, height),
                        (x+half_x, y+half_y, height), (x-half_x, y+half_y, height))
            lines.extend(f"v {vx:.4f} {vy:.4f} {vz:.4f}" for vx, vy, vz in vertices)
            lines.extend(
                "f " + " ".join(f"{vertex_offset + index - 1}//{normal_index}"
                                 for index in face)
                for normal_index, face in enumerate(faces, start=1)
            )
            vertex_offset += 8
    MESH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    red, green, blue, alpha = visual_model["color_rgba"]
    MATERIAL.write_text(
        "# Generated from profiles/environments/paddy_field.yaml\n"
        "newmtl rice_green\n"
        f"Ka {red} {green} {blue}\n"
        f"Kd {red} {green} {blue}\n"
        "Ks 0.05 0.05 0.05\n"
        "Ns 8.0\n"
        f"d {alpha}\n"
        "illum 2\n",
        encoding="utf-8",
    )

    # Render all four sides as one rectangular ring, so no side can cross another.
    outer_x, outer_y = half_length, half_width
    inner_x = half_length - bund_thickness
    inner_y = half_width - bund_thickness
    boundary_vertices = (
        (-outer_x, -outer_y, 0.0), (outer_x, -outer_y, 0.0),
        (outer_x, outer_y, 0.0), (-outer_x, outer_y, 0.0),
        (-inner_x, -inner_y, 0.0), (inner_x, -inner_y, 0.0),
        (inner_x, inner_y, 0.0), (-inner_x, inner_y, 0.0),
        (-outer_x, -outer_y, bund_height), (outer_x, -outer_y, bund_height),
        (outer_x, outer_y, bund_height), (-outer_x, outer_y, bund_height),
        (-inner_x, -inner_y, bund_height), (inner_x, -inner_y, bund_height),
        (inner_x, inner_y, bund_height), (-inner_x, inner_y, bund_height),
    )
    boundary_faces = (
        ((9, 10, 14, 13), 1), ((10, 11, 15, 14), 1),
        ((11, 12, 16, 15), 1), ((12, 9, 13, 16), 1),
        ((1, 5, 6, 2), 2), ((2, 6, 7, 3), 2),
        ((3, 7, 8, 4), 2), ((4, 8, 5, 1), 2),
        ((1, 2, 10, 9), 3), ((2, 3, 11, 10), 4),
        ((3, 4, 12, 11), 5), ((4, 1, 9, 12), 6),
        ((5, 13, 14, 6), 5), ((6, 14, 15, 7), 6),
        ((7, 15, 16, 8), 3), ((8, 16, 13, 5), 4),
    )
    boundary_lines = [
        "# Generated from profiles/environments/paddy_field.yaml",
        "mtllib paddy_boundary.mtl", "o paddy_boundary", "usemtl bund_brown",
        "vn 0 0 1", "vn 0 0 -1", "vn 0 -1 0", "vn 1 0 0",
        "vn 0 1 0", "vn -1 0 0",
    ]
    boundary_lines.extend(f"v {x:.4f} {y:.4f} {z:.4f}"
                          for x, y, z in boundary_vertices)
    boundary_lines.extend(
        "f " + " ".join(f"{index}//{normal}" for index in face)
        for face, normal in boundary_faces
    )
    BOUNDARY_MESH.write_text("\n".join(boundary_lines) + "\n", encoding="utf-8")
    bund_red, bund_green, bund_blue, bund_alpha = bund["color_rgba"]
    BOUNDARY_MATERIAL.write_text(
        "# Generated from profiles/environments/paddy_field.yaml\n"
        "newmtl bund_brown\n"
        f"Ka {bund_red} {bund_green} {bund_blue}\n"
        f"Kd {bund_red} {bund_green} {bund_blue}\n"
        "Ks 0.03 0.03 0.03\nNs 4.0\n"
        f"d {bund_alpha}\nillum 2\n",
        encoding="utf-8",
    )

    boundary = element(world, "model", name="field_boundary")
    element(boundary, "static", "true")
    boundary_link = element(boundary, "link", name="rectangular_frame")
    boundary_visual = element(boundary_link, "visual", name="continuous_boundary")
    boundary_geometry = element(boundary_visual, "geometry")
    boundary_mesh = element(boundary_geometry, "mesh")
    element(boundary_mesh, "uri", "../meshes/paddy_boundary.obj")
    boundary_material = element(boundary_visual, "material")
    element(boundary_material, "ambient", bund_color)
    element(boundary_material, "diffuse", bund_color)

    model = element(world, "model", name="crop_field")
    element(model, "static", "true")
    link = element(model, "link", name="plants")
    visual = element(link, "visual", name="individual_rice_plants")
    geometry = element(visual, "geometry")
    mesh = element(geometry, "mesh")
    element(mesh, "uri", "../meshes/paddy_crops.obj")
    material = element(visual, "material")
    element(material, "ambient", color)
    element(material, "diffuse", color)

    ET.indent(tree, space="  ")
    tree.write(WORLD, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
