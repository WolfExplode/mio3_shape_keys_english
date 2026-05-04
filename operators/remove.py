import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface, pgettext_rpt
from ..classes.operator import Mio3SKOperator
from ..utils.ext_data import refresh_data
from ..utils.utils import is_local_obj, has_shape_key


class OBJECT_OT_mio3sk_remove(Mio3SKOperator):
    bl_idname = "object.mio3sk_shape_key_remove"
    bl_label = "Remove Shape Key"
    bl_description = "Remove shape key from the object"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Target",
        items=[
            ("ACTIVE", "Active Shape Key", ""),
            ("SELECTED", "Selected Shape Keys", ""),
            ("ALL", "All Shape Keys", ""),
        ],
        options={"SKIP_SAVE"},
    )
    apply_mix: BoolProperty(
        name="Apply Shapes",
        description="Apply the current shape key mix before removing",
        default=False,
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        if self.mode != "ACTIVE" or event.alt:
            if event.alt:
                self.mode = "SELECTED"
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)
        
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        obj = context.active_object
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        if selected_len:
            layout.label(
                text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len),
                icon="SHAPEKEY_DATA",
            )
        col = layout.column()
        col.prop(self, "mode", expand=True)
        if self.mode == "ALL":
            col.prop(self, "apply_mix")

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}

        def remove_value_driver(shape_key):
            # Blender 5.1 can crash in driver evaluation if a driven key is deleted rapidly.
            # Remove the value driver first to keep depsgraph state consistent.
            if shape_key is None:
                return
            try:
                shape_key.driver_remove("value")
            except (TypeError, RuntimeError):
                pass

        if self.mode == "ACTIVE":
            active_kb = obj.active_shape_key
            if active_kb.lock_shape:
                self.report({"ERROR"}, "Active Shape Key is Locked")
                return {"CANCELLED"}
            remove_value_driver(active_kb)
            obj.shape_key_remove(active_kb)
        elif self.mode == "SELECTED":
            key_blocks = obj.data.shape_keys.key_blocks
            selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
            for kb in reversed(key_blocks):
                if kb.name not in selected_names or kb.lock_shape:
                    continue
                remove_value_driver(kb)
                obj.shape_key_remove(kb)
        else:
            if obj.data.shape_keys:
                for kb in obj.data.shape_keys.key_blocks:
                    remove_value_driver(kb)
            try:
                if self.apply_mix:
                    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                else:
                    bpy.ops.object.shape_key_remove(all=True)
            except Exception as e:
                self.report({"ERROR"}, str(e))

        if not obj.data.shape_keys:
            obj.mio3sk.ext_data.clear()
            obj.mio3sk.store_names.clear()

        refresh_data(context, obj, check=True, group=True, filter=True)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_remove_drivers(Mio3SKOperator):
    bl_idname = "object.mio3sk_remove_drivers"
    bl_label = "Remove Drivers"
    bl_description = "Remove all drivers from selected shape keys"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Target",
        items=[
            ("ACTIVE", "Active Shape Key", ""),
            ("SELECTED", "Selected Shape Keys", ""),
            ("ALL", "All Shape Keys", ""),
        ],
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        if self.mode != "ACTIVE":
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        obj = context.active_object
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        if selected_len:
            layout.label(
                text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len),
                icon="SHAPEKEY_DATA",
            )
        layout.prop(self, "mode", expand=True)

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks

        if self.mode == "ACTIVE":
            active_kb = obj.active_shape_key
            selected_names = {active_kb.name} if active_kb else set()
        elif self.mode == "SELECTED":
            selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
        else:
            selected_names = {kb.name for kb in key_blocks}

        removed_count = 0
        for kb in key_blocks:
            if kb.name not in selected_names:
                continue
            try:
                if kb.driver_remove("value"):
                    removed_count += 1
            except TypeError:
                pass

        if removed_count > 0:
            self.report({"INFO"}, pgettext_rpt("Removed {} drivers").format(removed_count))

        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_remove,
    OBJECT_OT_mio3sk_remove_drivers,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
