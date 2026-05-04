import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty
from ..classes.operator import Mio3SKOperator


class OBJECT_OT_mio3sk_set_prop(Mio3SKOperator):
    bl_idname = "object.mio3sk_set_props"
    bl_label = "Set Shape Key Properties"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Type",
        items=[
            ("slider_min", "Range Min", ""),
            ("slider_max", "Range Max", ""),
        ],
    )
    index: IntProperty(name="Index", default=-1, options={"HIDDEN", "SKIP_SAVE"})
    value: FloatProperty(name="Value", default=0, options={"HIDDEN", "SKIP_SAVE"})
    add: BoolProperty(name="Add", default=False, options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks
        if not (0 <= self.index < len(key_blocks)):
            return {"CANCELLED"}

        kb = key_blocks[self.index]
        if kb is None:
            return {"CANCELLED"}

        if self.mode == "slider_min":
            if self.add:
                kb.slider_min += self.value
            else:
                kb.slider_min = self.value
        elif self.mode == "slider_max":
            if self.add:
                kb.slider_max += self.value
                kb.value = kb.slider_max
            else:
                kb.slider_max = self.value

        return {"FINISHED"}


classes = [OBJECT_OT_mio3sk_set_prop]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
