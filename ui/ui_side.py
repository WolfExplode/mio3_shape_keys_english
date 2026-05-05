import bpy
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes.operator import Mio3SKSidePanel
from ..utils.utils import is_obj, has_shape_key
from ..icons import icons
from ..globals import get_preferences
from ..operators.morph_brush import MORPH_ATTR_NAME


class MIO3SK_PT_side_main(Mio3SKSidePanel):
    bl_label = "Mio3 Shape Keys"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return is_obj(obj) and has_shape_key(obj)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("mesh.mio3sk_reset", text=tt_iface("Reset to Basis"), icon_value=icons.eraser)
        row.operator("mesh.mio3sk_smooth_shape", text="Smooth", icon_value=icons.smooth)
        row.menu("MIO3SK_MT_side", text="", icon="DOWNARROW_HLT")
        col.separator()
        row = col.row(align=True)
        row.operator("mesh.mio3sk_copy", text="Copy", icon="COPYDOWN")
        row.operator("mesh.mio3sk_paste", text="Paste", icon="PASTEDOWN")


class MIO3SK_PT_sub_blend(Mio3SKSidePanel):
    bl_label = "Blend"
    bl_parent_id = "MIO3SK_PT_side_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object.data.shape_keys is not None

    def draw(self, context):
        prop_s = context.scene.mio3sk
        prop_w = context.window_manager.mio3sk
        shape_keys = context.active_object.data.shape_keys

        layout = self.layout
        row = layout.row(align=True)
        row.prop_search(prop_w, "blend_source_name", shape_keys, "key_blocks", text="")
        row.operator("wm.mio3sk_blend_set_key", icon="TRIA_LEFT", text="")

        col = layout.column(align=False)
        split = col.split(factor=0.5, align=True)
        split.prop(prop_s, "blend", text="")
        split.operator("mesh.mio3sk_blend", text="Blend")["blend"] = prop_s.blend
        split = col.split(factor=0.58)
        # row = split.row(align=True)
        # row.operator("mesh.mio3sk_blend", text="0.05")["blend"] = 0.05


class MIO3SK_PT_sub_delta_repair(Mio3SKSidePanel):
    bl_label = "Expression repair"
    bl_parent_id = "MIO3SK_PT_side_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object.data.shape_keys is not None

    def draw(self, context):
        prop_w = context.window_manager.mio3sk
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="After using Apply to Basis", icon="INFO")
        col.label(text="Repair broken expressions", icon="BLANK1")
        row = col.row(align=True)
        shape_keys = context.active_object.data.shape_keys
        row.prop_search(prop_w, "apply_to_basis", shape_keys, "key_blocks", text="")
        # row.enabled = False
        col.operator("mesh.mio3sk_repair")


class MIO3SK_PT_sub_morph(Mio3SKSidePanel):
    bl_label = "Morph Brush"
    bl_parent_id = "MIO3SK_PT_side_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.data.shape_keys is not None

    def draw(self, context):
        obj = context.active_object
        prop_w = context.window_manager.mio3sk
        shape_keys = obj.data.shape_keys

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop_search(prop_w, "copy_source", shape_keys, "key_blocks", text="Target")
        row.operator("mesh.mio3sk_copy", text="", icon="TRIA_LEFT")

        col.separator()

        attr_exists = obj.data.color_attributes.get(MORPH_ATTR_NAME) is not None
        if attr_exists:
            col.label(text="Weight attr: ready", icon="CHECKMARK")
        else:
            col.label(text="Weight attr: not set up", icon="ERROR")

        col.separator()
        col.operator("object.mio3sk_morph_setup", text="Setup Morph Weights", icon="BRUSH_DATA")
        col.operator("object.mio3sk_morph_apply", text="Apply Morph", icon="CHECKMARK")


classes = [
    MIO3SK_PT_side_main,
    MIO3SK_PT_sub_blend,
    MIO3SK_PT_sub_delta_repair,
    MIO3SK_PT_sub_morph,
]


def register():
    prefs = get_preferences()
    for cls in classes:
        cls.bl_category = prefs.category
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
