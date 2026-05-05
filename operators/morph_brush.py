import bpy
import numpy as np
from bpy.props import BoolProperty, FloatProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key

MORPH_ATTR_NAME = "mio3sk_morph"


class OBJECT_OT_mio3sk_morph_setup(Mio3SKOperator):
    bl_idname = "object.mio3sk_morph_setup"
    bl_label = "Setup Morph Weights"
    bl_description = (
        "Create the mio3sk_morph color attribute (white = no effect, black = full blend), "
        "and set it as the active color attribute. Switch to Vertex Paint and your preferred brush yourself"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        mesh = obj.data

        attr = mesh.color_attributes.get(MORPH_ATTR_NAME)
        if attr is None:
            attr = mesh.color_attributes.new(
                name=MORPH_ATTR_NAME,
                type="FLOAT_COLOR",
                domain="POINT",
            )
            # Initialize to white — white = no influence, black = full influence
            num_verts = len(mesh.vertices)
            white_buf = np.ones(num_verts * 4, dtype=np.float32)
            attr.data.foreach_set("color", white_buf)

        mesh.color_attributes.active_color = attr

        self.report(
            {"INFO"},
            "Morph weight attribute ready. Use Vertex Paint to paint black, then Apply Morph.",
        )
        return {"FINISHED"}


class OBJECT_OT_mio3sk_morph_apply(Mio3SKOperator):
    bl_idname = "object.mio3sk_morph_apply"
    bl_label = "Apply Morph"
    bl_description = (
        "Blend the active shape key toward the morph target using the painted weight. "
        "Black areas blend fully, white areas are unchanged"
    )
    bl_options = {"REGISTER", "UNDO"}

    blend: FloatProperty(name="Blend", default=1.0, min=0.0, max=2.0, step=10)
    add: BoolProperty(
        name="Add",
        description="Add the shape delta on top of the current shape instead of interpolating",
        default=False,
    )
    clear: BoolProperty(
        name="Clear After Apply",
        description="Reset the morph weight attribute to white after applying",
        default=True,
    )
    from_timer: BoolProperty(default=False, options={"SKIP_SAVE", "HIDDEN"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            return False
        return valid_shape_key(obj) and bool(context.window_manager.mio3sk.copy_source)

    def execute(self, context):
        if not self.from_timer:
            bpy.ops.ed.undo_push(message="Apply Morph")
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        prop_w = context.window_manager.mio3sk
        morph_source_name = prop_w.copy_source

        key_blocks = obj.data.shape_keys.key_blocks
        source_kb = key_blocks.get(morph_source_name)
        if not source_kb:
            self.report({"WARNING"}, "Morph target shape key not found")
            return {"CANCELLED"}

        target_kb = obj.active_shape_key
        if not target_kb:
            return {"CANCELLED"}

        if target_kb.name == morph_source_name:
            self.report({"WARNING"}, "Active shape key and morph target are the same")
            return {"CANCELLED"}

        mesh = obj.data
        attr = mesh.color_attributes.get(MORPH_ATTR_NAME)
        if not attr:
            self.report({"WARNING"}, "Morph attribute not found. Run Setup Morph Weights first.")
            return {"CANCELLED"}

        num_verts = len(mesh.vertices)

        color_buf = np.zeros(num_verts * 4, dtype=np.float32)
        attr.data.foreach_get("color", color_buf)
        weights = 1.0 - color_buf.reshape(-1, 4)[:, 0]  # inverted R: black = full weight, white = none

        if weights.max() < 1e-6:
            self.report({"WARNING"}, "No morph weight painted. Paint black areas first.")
            return {"CANCELLED"}

        source_buf = np.empty(num_verts * 3, dtype=np.float32)
        target_buf = np.empty(num_verts * 3, dtype=np.float32)
        source_kb.data.foreach_get("co", source_buf)
        target_kb.data.foreach_get("co", target_buf)

        source_co = source_buf.reshape(-1, 3)
        target_co = target_buf.reshape(-1, 3)

        effective = np.clip(weights * self.blend, 0.0, 1.0)[:, np.newaxis]

        if self.add:
            basis_kb = obj.data.shape_keys.reference_key
            basis_buf = np.empty(num_verts * 3, dtype=np.float32)
            basis_kb.data.foreach_get("co", basis_buf)
            basis_co = basis_buf.reshape(-1, 3)
            result = target_co + (source_co - basis_co) * effective
        else:
            result = target_co + (source_co - target_co) * effective

        target_kb.data.foreach_set("co", result.reshape(-1))

        if self.clear:
            white_buf = np.ones(num_verts * 4, dtype=np.float32)
            attr.data.foreach_set("color", white_buf)

        mesh.update()
        obj.data.update_tag()
        obj.data.shape_keys.update_tag()
        self.print_time()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.4)
        split.label(text="Blend")
        split.prop(self, "blend", text="")
        split = layout.split(factor=0.4)
        split.label(text="Add")
        split.prop(self, "add", text="")
        split = layout.split(factor=0.4)
        split.label(text="Clear After Apply")
        split.prop(self, "clear", text="")


classes = [OBJECT_OT_mio3sk_morph_setup, OBJECT_OT_mio3sk_morph_apply]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
