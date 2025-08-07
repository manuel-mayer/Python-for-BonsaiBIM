#Get all VirtualElements, find their respective walls and transfer their properties for more advance ifc native PfV-workflows.
import bpy

from mathutils import Vector
import bonsai.tool as tool

# This script finds all IfcVirtualElement objects in the current Blender scene by checking for the 'BIMObjectProperties' property.
text_name = "IfcVirtualElements_Report"
if text_name in bpy.data.texts:
    text_block = bpy.data.texts[text_name]
    text_block.clear()
else:
    text_block = bpy.data.texts.new(text_name)

virtual_elements = []
wall_elements = []
for obj in bpy.data.objects:
    if "BIMObjectProperties" in obj:
        props = obj["BIMObjectProperties"]
        props_str = str(props)
        if "VirtualElement" in props_str:
            virtual_elements.append(obj)
        if "Wall" in props_str:
            wall_elements.append(obj)
text_block.write(f"Found {len(virtual_elements)} IfcVirtualElement objects in the scene.\n")
for obj in virtual_elements:
    # Deselect all, select only this object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Set origin to center of mass (geometry)
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
    # Now get the new centerpoint (object origin in world space)
    center = obj.matrix_world.translation
    text_block.write(f"Name: {obj.name}, Centerpoint: ({center.x:.3f}, {center.y:.3f}, {center.z:.3f})\n")

# Now process IfcWall objects and their bounding boxes
text_block.write(f"\nFound {len(wall_elements)} IfcWall objects in the scene.\n")


# Compute bounding boxes for all walls

wall_bboxes = []
for obj in wall_elements:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs = [v.x for v in bbox_corners]
    ys = [v.y for v in bbox_corners]
    zs = [v.z for v in bbox_corners]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    # Use BonsaiBIM to get the IFC entity and IfcWallType name
    ifc_entity = tool.Ifc.get_entity(obj)
    walltype_name = None
    material_name = None
    if ifc_entity:
        # Try to get the type object (IfcWallType) and its Name
        try:
            if hasattr(ifc_entity, 'IsTypedBy') and ifc_entity.IsTypedBy:
                type_rel = ifc_entity.IsTypedBy[0]
                if hasattr(type_rel, 'RelatingType'):
                    walltype = type_rel.RelatingType
                    walltype_name = getattr(walltype, 'Name', None)
        except Exception:
            pass
        # Try to get the IfcMaterial name
        try:
            if hasattr(ifc_entity, 'HasAssociations') and ifc_entity.HasAssociations:
                for assoc in ifc_entity.HasAssociations:
                    # IfcRelAssociatesMaterial
                    if hasattr(assoc, 'RelatingMaterial'):
                        mat = assoc.RelatingMaterial
                        # IfcMaterialLayerSet or IfcMaterial
                        if hasattr(mat, 'Name'):
                            material_name = mat.Name
                        elif hasattr(mat, 'ForLayerSet') and hasattr(mat.ForLayerSet, 'MaterialLayers'):
                            # IfcMaterialLayerSet
                            layers = mat.ForLayerSet.MaterialLayers
                            if layers and hasattr(layers[0], 'Material') and hasattr(layers[0].Material, 'Name'):
                                material_name = layers[0].Material.Name
        except Exception:
            pass
    wall_bboxes.append({
        'name': obj.name,
        'min_x': min_x, 'max_x': max_x,
        'min_y': min_y, 'max_y': max_y,
        'min_z': min_z, 'max_z': max_z,
        'type': walltype_name,
        'material': material_name
    })
    text_block.write(f"Name: {obj.name}, BoundingBox: X({min_x:.3f} to {max_x:.3f}), Y({min_y:.3f} to {max_y:.3f}), Z({min_z:.3f} to {max_z:.3f})\n")

# Check if any virtual element centerpoint is inside any wall bounding box
text_block.write("\nVirtualElement-to-Wall containment results:\n")
for vobj in virtual_elements:
    vcenter = vobj.matrix_world.translation
    found = False
    for wall in wall_bboxes:
        if (wall['min_x'] <= vcenter.x <= wall['max_x'] and
            wall['min_y'] <= vcenter.y <= wall['max_y'] and
            wall['min_z'] <= vcenter.z <= wall['max_z']):
            text_block.write(f"{vobj.name} is inside wall {wall['name']} (WallTypeName: {wall['type']}, Material: {wall['material']})\n")
            found = True
    if not found:
        text_block.write(f"{vobj.name} is not inside any wall\n")
