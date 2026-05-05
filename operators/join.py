import bpy
import bmesh
import numpy as np
from bpy.props import BoolProperty, EnumProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key, get_unique_name
from ..utils.ext_data import clear_filter, refresh_data

# shape_key_transfer_op = bpy.ops.object.shape_key_transfer.get_rna_type()
# join_shapes_op = bpy.ops.object.join_shapes.get_rna_type()


class OBJECT_OT_mio3sk_join_keys(Mio3SKOperator):
    bl_idname = "object.mio3sk_join_keys"
    bl_label = "Join Shape Keys"
    bl_description = "Merge shape keys with current values into new shape key"
    bl_options = {"REGISTER", "UNDO"}
    target: EnumProperty(
        name="Target",
        items=[
            ("NEW", "Create New", ""),
            ("ACTIVE", "Active Shape Key", ""),
        ],
        options={"SKIP_SAVE"},
    )
    clear_value: BoolProperty(name="Clear value", default=False, options={"SKIP_SAVE"})
    selected_only: BoolProperty(name="Selected keys only", default=False, options={"SKIP_SAVE"})
    # clear_shape: BoolProperty(name="形状を初期化", default=True, options={"SKIP_SAVE"})

    def _get_selected_names(self, obj):
        names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
        if not names:
            names.add(obj.active_shape_key.name)
        return names

    def _snapshot_and_zero_unselected(self, key_blocks, selected_names):
        snapshot = []
        for kb in key_blocks:
            if kb.name not in selected_names and kb.value != 0.0:
                snapshot.append((kb, kb.value))
                kb.value = 0.0
        return snapshot

    def _restore_values(self, snapshot):
        for kb, value in snapshot:
            kb.value = value

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        obj = context.active_object
        self.layout.label(text="Join To")
        self.layout.prop(self, "target", expand=True)
        self.layout.prop(self, "clear_value")
        if any(ext.select for ext in obj.mio3sk.ext_data):
            self.layout.prop(self, "selected_only")
        # self.layout.prop(self, "clear_shape")

    def execute(self, context):
        obj = context.active_object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks

        if self.target == "ACTIVE":
            if not is_local_obj(obj) or not valid_shape_key(obj):
                return {"CANCELLED"}

            basis_kb = shape_keys.reference_key
            active_kb = obj.active_shape_key

            snapshot = []
            selected_names_for_mix = None
            if self.selected_only:
                selected_names_for_mix = self._get_selected_names(obj)
                selected_names_for_mix.add(active_kb.name)
                selected_names_for_mix.add(basis_kb.name)
                snapshot = self._snapshot_and_zero_unselected(key_blocks, selected_names_for_mix)

            if self.selected_only and selected_names_for_mix is not None:
                use_key_blocks = [
                    kb
                    for kb in key_blocks
                    if kb.name in selected_names_for_mix and (kb.value or active_kb == kb)
                ]
            else:
                use_key_blocks = [kb for kb in key_blocks if kb.value or active_kb == kb]

            if len(use_key_blocks) < 1:
                if snapshot:
                    self._restore_values(snapshot)
                return {"CANCELLED"}

            new_kb = obj.shape_key_add(name="__tmp__", from_mix=True)
            if snapshot:
                self._restore_values(snapshot)

            v_len = len(obj.data.vertices)

            shape_co_flat = np.empty(v_len * 3, dtype=np.float32)
            new_kb.data.foreach_get("co", shape_co_flat)

            if basis_kb == active_kb:
                shape_co = shape_co_flat.reshape(-1, 3)
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.verts.ensure_lookup_table()
                for i in range(len(bm.verts)):
                    bm.verts[i].co = shape_co[i]
                bm.to_mesh(obj.data)
                bm.free()
            else:
                active_kb.data.foreach_set("co", shape_co_flat)

            bas_co_flat = np.empty(v_len * 3, dtype=np.float32)
            basis_kb.data.foreach_get("co", bas_co_flat)

            for kb in reversed(use_key_blocks):
                if kb != active_kb:
                    if self.clear_value:
                        kb.value = 0.0
                    # if self.clear_shape:
                    #     kb.data.foreach_set("co", bas_co_flat)

            obj.shape_key_remove(new_kb)
            if basis_kb != active_kb:
                active_kb.value = 1.0
            obj.active_shape_key_index = key_blocks.find(active_kb.name)
            obj.data.update()

            clear_filter(context, obj)
        else:
            snapshot = []
            if self.selected_only:
                mix_names = self._get_selected_names(obj)
                mix_names.add(shape_keys.reference_key.name)
                snapshot = self._snapshot_and_zero_unselected(key_blocks, mix_names)
            new_key = obj.shape_key_add(name=get_unique_name(key_blocks.keys(), "Key"), from_mix=True)
            if snapshot:
                self._restore_values(snapshot)
            obj.active_shape_key_index = key_blocks.find(new_key.name)

        refresh_data(context, obj, check=True, group=True, filter=True)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_join_keys)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_join_keys)
