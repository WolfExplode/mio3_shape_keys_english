import bpy
import numpy as np
from bpy.props import BoolProperty, StringProperty, EnumProperty
from ..classes.operator import Mio3SKOperator


class OBJECT_OT_mio3sk_bake_attr(Mio3SKOperator):
    bl_idname = "object.mio3sk_bake_attr"
    bl_label = "シェイプキーを属性にベイク"
    bl_description = "シェイプキーの移動量または位置をメッシュ属性にベイクします"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Target",
        items=[
            ("ACTIVE", "Active Shape Key", ""),
            ("SELECTED", "Selected Shape Keys", ""),
            ("ALL", "All Shape Keys", ""),
        ],
    )
    delta_keys_only: BoolProperty(name="差分があるキーのみ", default=True)
    prefix: StringProperty(name="Prefix", default="ShapeKey_")
    data_type: EnumProperty(
        name="Type",
        items=[
            ("DELTA", "Delta", "移動量"),
            ("CO", "Position", "位置"),
        ],
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks
        basis_kb = shape_keys.reference_key

        if self.mode == "ACTIVE":
            target_keys = [obj.active_shape_key]
        elif self.mode == "SELECTED":
            selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
            target_keys = [kb for kb in key_blocks if kb.name in selected_names]
        else:
            target_keys = list(key_blocks[1:])

        v_len = len(obj.data.vertices)
        basis_co_flat = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_flat)

        shape_co_flat = np.empty(v_len * 3, dtype=np.float32)

        for kb in target_keys:
            if kb is None or kb == basis_kb:
                continue

            kb.data.foreach_get("co", shape_co_flat)

            if self.delta_keys_only and not np.any(np.abs(basis_co_flat - shape_co_flat) > 0.00001):
                continue

            attr_name = "{}{}".format(self.prefix, kb.name)
            attr = obj.data.attributes.get(attr_name)
            if not attr:
                attr = obj.data.attributes.new(name=attr_name, type="FLOAT_VECTOR", domain="POINT")

            if self.data_type == "DELTA":
                attr.data.foreach_set("vector", shape_co_flat - basis_co_flat)
            else:
                attr.data.foreach_set("vector", shape_co_flat)

        self.print_time()
        return {"FINISHED"}


classes = [OBJECT_OT_mio3sk_bake_attr]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
