import bpy
import numpy as np
from bpy.props import FloatProperty
from bpy.app.translations import pgettext_rpt
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key, get_unique_name


class OBJECT_OT_mio3sk_create_vertex_group(Mio3SKOperator):
    bl_idname = "object.mio3sk_create_vertex_group"
    bl_label = "Create Vertex Group"
    bl_description = "Create vertex group from selected shape keys"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        description="Minimum distance to consider vertex as affected (moved)",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and has_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        if not is_local_obj(context.active_object) or not has_shape_key(context.active_object):
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "threshold")

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks
        basis_kb = obj.data.shape_keys.reference_key
        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}

        if not selected_names:
            self.report({"WARNING"}, pgettext_rpt("No shape keys selected"))
            return {"CANCELLED"}

        v_len = len(obj.data.vertices)
        basis_co_flat = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_flat)
        basis_co = basis_co_flat.reshape(-1, 3)

        vertex_group_names = set(obj.vertex_groups.keys())
        count = 0
        renamed = []
        threshold = self.threshold

        for kb in key_blocks:
            if kb.name not in selected_names or kb == basis_kb:
                continue
            shape_co_flat = np.empty(v_len * 3, dtype=np.float32)
            kb.data.foreach_get("co", shape_co_flat)
            shape_co = shape_co_flat.reshape(-1, 3)
            diff = np.linalg.norm(basis_co - shape_co, axis=1)
            affected = diff > threshold

            if not np.any(affected):
                continue

            if kb.name in vertex_group_names:
                renamed.append(kb.name)
            name = get_unique_name(vertex_group_names, kb.name)
            vertex_group_names.add(name)
            vgroup = obj.vertex_groups.new(name=name)

            affected_indices = np.where(affected)[0].astype(int).tolist()
            vgroup.add(affected_indices, 1.0, "REPLACE")
            count += 1

        if count > 0:
            self.report({"INFO"}, pgettext_rpt("Created {} vertex groups").format(count))
        else:
            self.report({"WARNING"}, pgettext_rpt("No vertices moved beyond threshold in selected keys"))
        if renamed:
            self.report({"WARNING"}, pgettext_rpt("Vertex group(s) already exist, used unique names: {}").format(", ".join(renamed)))

        self.print_time()
        return {"FINISHED"}


classes = [OBJECT_OT_mio3sk_create_vertex_group]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
