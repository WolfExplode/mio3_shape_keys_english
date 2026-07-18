import bpy
import bmesh
import numpy as np
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty, CollectionProperty
from bpy.app.translations import pgettext_rpt
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key
from ..utils.mesh import find_x_mirror_verts


def vertex_group_weights(obj, group_name):
    vgroup = obj.vertex_groups.get(group_name)
    if vgroup is None:
        return None
    num_verts = len(obj.data.vertices)
    weights = np.zeros(num_verts, dtype=np.float32)
    group_index = vgroup.index
    for vert in obj.data.vertices:
        for group in vert.groups:
            if group.group == group_index:
                weights[vert.index] = group.weight
                break
    return weights


def vertex_group_weights_bmesh(bm, obj, group_name):
    vgroup = obj.vertex_groups.get(group_name)
    if vgroup is None:
        return None
    deform = bm.verts.layers.deform.active
    if deform is None:
        deform = bm.verts.layers.deform.verify()
    group_index = vgroup.index
    num_verts = len(bm.verts)
    weights = np.zeros(num_verts, dtype=np.float32)
    for vert in bm.verts:
        weights[vert.index] = vert[deform].get(group_index, 0.0)
    return weights


def sculpt_mask_weights(obj):
    mesh = obj.data
    num_verts = len(mesh.vertices)
    weights = np.ones(num_verts, dtype=np.float32)
    mask_attr = mesh.vertex_paint_mask
    if mask_attr is None:
        return weights
    mask_data = mask_attr.data if hasattr(mask_attr, "data") else mask_attr
    if len(mask_data) != num_verts:
        return weights
    mask = np.empty(num_verts, dtype=np.float32)
    mask_data.foreach_get("value", mask)
    weights[:] = mask
    return weights


def sculpt_mask_weights_bmesh(bm):
    num_verts = len(bm.verts)
    weights = np.ones(num_verts, dtype=np.float32)
    layer = bm.verts.layers.float.get(".sculpt_mask")
    if layer is None:
        return weights
    for vert in bm.verts:
        weights[vert.index] = vert[layer]
    return weights


def apply_shape_blend(target_co, basis_co, source_co, subtract_co, blend, add_mode, mask=None):
    if mask is None:
        pos_w = blend
        neg_w = -blend
    else:
        pos_w = mask
        neg_w = -mask

    result = np.asarray(target_co, dtype=np.float32)
    if add_mode:
        if source_co is not None:
            result = result + (source_co - basis_co) * pos_w
        if subtract_co is not None:
            result = result + (subtract_co - basis_co) * neg_w
        return result

    if source_co is not None:
        result = (1 - pos_w) * result + pos_w * source_co
    if subtract_co is not None:
        result = (1 - neg_w) * result + neg_w * subtract_co
    return result


class OP_PG_mio3sk_blend(PropertyGroup):
    pass


class MESH_OT_mio3sk_blend(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_blend"
    bl_label = "Blend shape keys"
    bl_description = "Blend shape keys"
    bl_options = {"REGISTER", "UNDO"}

    blend: FloatProperty(name="Blend Strength", default=1, min=-2, max=2, step=10)
    smooth: BoolProperty(
        name="Smooth",
        description="Taper the blend across selected vertices using the falloff curve, instead of applying it uniformly",
        default=False,
    )
    add: BoolProperty(name="Add", default=False)
    falloff: EnumProperty(
        name="Falloff",
        items=[
            ("gaussian", "Gaussian", ""),
            ("sphere", "Sphere", ""),
            ("arc", "Arc", ""),
            ("linear", "Linear", ""),
        ],
    )
    blend_source: StringProperty(name="Shape")
    blend_subtract: StringProperty(
        name="Subtract Shape",
        description="Blend this shape with inverse blend strength",
        default="",
    )
    blend_vertex_group: StringProperty(
        name="Vertex Group",
        description="Only influence selected vertex group",
        default="",
    )
    blend_sculpt_mask: BoolProperty(
        name="Mask",
        description="Use sculpt mask for blend region",
        default=False,
    )
    from_history: StringProperty(name="Select from history", options={"SKIP_SAVE"})
    select_history: CollectionProperty(
        type=OP_PG_mio3sk_blend,
        name="Select History",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj)
    
    def invoke(self, context, event):
        obj = context.active_object
        prop_w = context.window_manager.mio3sk

        if not is_local_obj(obj):
            return {"CANCELLED"}

        if not valid_shape_key(obj):
            self.report({"WARNING"}, pgettext_rpt("Has not Shape Keys"))
            return {"CANCELLED"}

        key_block_names = obj.data.shape_keys.key_blocks.keys()
        self.select_history.clear()
        for history in context.window_manager.mio3sk.select_history:
            if history.name in key_block_names:
                self.select_history.add().name = history.name

        self.blend_source = prop_w.blend_source_name
        self.blend_subtract = prop_w.blend_subtract_name
        self.blend_vertex_group = context.scene.mio3sk.blend_vertex_group
        self.blend_sculpt_mask = context.scene.mio3sk.blend_sculpt_mask
        if event.alt:
            self.blend = -self.blend
        return self.execute(context)

    def execute(self, context):
        result = self._execute(context)
        if "FINISHED" in result:
            context.scene.mio3sk.blend = self.blend
        return result

    def _execute(self, context):
        self.start_time()
        obj = context.active_object
        if not obj.active_shape_key:
            return {"CANCELLED"}

        blend_source_name = self.from_history if self.from_history else self.blend_source
        if not (blend_source := obj.data.shape_keys.key_blocks.get(blend_source_name)):
            return {"CANCELLED"}

        blend_subtract = None
        if self.blend_subtract:
            blend_subtract = obj.data.shape_keys.key_blocks.get(self.blend_subtract)
            if blend_subtract is None:
                self.report({"WARNING"}, pgettext_rpt("Subtract shape key not found"))
                return {"CANCELLED"}

        if self.blend_sculpt_mask or self.blend_vertex_group:
            if self.blend_sculpt_mask:
                if obj.mode == "EDIT":
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.verts.ensure_lookup_table()
                    weights = sculpt_mask_weights_bmesh(bm)
                else:
                    weights = sculpt_mask_weights(obj)
            else:
                if obj.mode == "EDIT":
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.verts.ensure_lookup_table()
                    weights = vertex_group_weights_bmesh(bm, obj, self.blend_vertex_group)
                else:
                    weights = vertex_group_weights(obj, self.blend_vertex_group)
                if weights is None:
                    self.report({"WARNING"}, pgettext_rpt("Vertex group not found"))
                    return {"CANCELLED"}

            if obj.mode == "EDIT":
                return self.execute_blend_mask_edit(context, obj, blend_source, blend_subtract, weights)
            return self.execute_blend_mask(context, obj, blend_source, blend_subtract, weights)

        if obj.mode == "OBJECT":
            basis_kb = obj.data.shape_keys.reference_key
            target_kb = obj.active_shape_key
            num_verts = len(obj.data.vertices)

            basis_buf = np.empty(num_verts * 3, dtype=np.float32)
            source_buf = np.empty(num_verts * 3, dtype=np.float32)
            target_buf = np.empty(num_verts * 3, dtype=np.float32)

            basis_kb.data.foreach_get("co", basis_buf)
            blend_source.data.foreach_get("co", source_buf)
            target_kb.data.foreach_get("co", target_buf)

            basis_co = basis_buf.reshape((num_verts, 3))
            source_co = source_buf.reshape((num_verts, 3))
            target_co = target_buf.reshape((num_verts, 3))

            subtract_co = None
            if blend_subtract is not None:
                subtract_buf = np.empty(num_verts * 3, dtype=np.float32)
                blend_subtract.data.foreach_get("co", subtract_buf)
                subtract_co = subtract_buf.reshape((num_verts, 3))

            result = apply_shape_blend(
                target_co, basis_co, source_co, subtract_co, self.blend, self.add
            )

            target_kb.data.foreach_set("co", result.reshape(num_verts * 3))
            obj.data.update()
            # self.print_time()
            return {"FINISHED"}

        if not self.smooth:
            try:
                bpy.ops.mesh.blend_from_shape(shape=blend_source_name, blend=self.blend, add=self.add)
                if blend_subtract is not None:
                    bpy.ops.mesh.blend_from_shape(
                        shape=self.blend_subtract, blend=-self.blend, add=self.add
                    )
            except:
                pass

            self.print_time()
            return {"FINISHED"}

        basis_kb = obj.data.shape_keys.reference_key

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        selected_verts = {v for v in bm.verts if v.select}
        if obj.use_mesh_mirror_x:
            selected_verts.update(find_x_mirror_verts(bm, selected_verts))

        if not selected_verts:
            self.report({"WARNING"}, pgettext_rpt("No vertices selected"))
            return {"CANCELLED"}

        selected_verts_list = sorted(selected_verts, key=lambda v: v.index)
        selected_verts_indices = [v.index for v in selected_verts_list]
        basis_co = np.array([basis_kb.data[i].co for i in selected_verts_indices])
        source_co = np.array([blend_source.data[i].co for i in selected_verts_indices])
        target_co = np.array([v.co for v in selected_verts_list])

        subtract_co = None
        if blend_subtract is not None:
            subtract_co = np.array([blend_subtract.data[i].co for i in selected_verts_indices])

        weights = self.calc_weights_shape(selected_verts_list, target_co)
        weights /= np.max(weights)
        mask = (weights * self.blend)[:, np.newaxis]

        result = apply_shape_blend(
            target_co, basis_co, source_co, subtract_co, self.blend, self.add, mask=mask
        )

        for v, new_co in zip(selected_verts_list, result):
            v.co = new_co

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}

    def execute_blend_mask(self, context, obj, blend_source, blend_subtract, weights):
        basis_kb = obj.data.shape_keys.reference_key
        target_kb = obj.active_shape_key
        num_verts = len(obj.data.vertices)
        basis_buf = np.empty(num_verts * 3, dtype=np.float32)
        source_buf = np.empty(num_verts * 3, dtype=np.float32)
        target_buf = np.empty(num_verts * 3, dtype=np.float32)

        basis_kb.data.foreach_get("co", basis_buf)
        blend_source.data.foreach_get("co", source_buf)
        target_kb.data.foreach_get("co", target_buf)

        basis_co = basis_buf.reshape((num_verts, 3))
        source_co = source_buf.reshape((num_verts, 3))
        target_co = target_buf.reshape((num_verts, 3))

        subtract_co = None
        if blend_subtract is not None:
            subtract_buf = np.empty(num_verts * 3, dtype=np.float32)
            blend_subtract.data.foreach_get("co", subtract_buf)
            subtract_co = subtract_buf.reshape((num_verts, 3))

        mask = (weights * self.blend)[:, np.newaxis]
        result = apply_shape_blend(
            target_co, basis_co, source_co, subtract_co, self.blend, self.add, mask=mask
        )

        target_kb.data.foreach_set("co", result.reshape(num_verts * 3))
        obj.data.update()
        self.print_time()
        return {"FINISHED"}

    def execute_blend_mask_edit(self, context, obj, blend_source, blend_subtract, weights):
        basis_kb = obj.data.shape_keys.reference_key

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        num_verts = len(bm.verts)
        indices = np.arange(num_verts)
        basis_co = np.array([basis_kb.data[i].co for i in indices])
        source_co = np.array([blend_source.data[i].co for i in indices])
        target_co = np.array([bm.verts[i].co for i in indices])

        subtract_co = None
        if blend_subtract is not None:
            subtract_co = np.array([blend_subtract.data[i].co for i in indices])

        mask = (weights * self.blend)[:, np.newaxis]
        result = apply_shape_blend(
            target_co, basis_co, source_co, subtract_co, self.blend, self.add, mask=mask
        )

        for i, new_co in enumerate(result):
            bm.verts[i].co = new_co

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)
        self.print_time()
        return {"FINISHED"}

    # ウェイト計算(シェイプ)
    def calc_weights_shape(self, selected_verts, target_co):
        vert_to_idx = {v: i for i, v in enumerate(selected_verts)}

        boundary_verts = []
        boundary_indices = []
        interior_indices = []

        for i, v in enumerate(selected_verts):
            is_boundary = False
            for edge in v.link_edges:
                other_v = edge.other_vert(v)
                if other_v not in vert_to_idx:
                    is_boundary = True
                    boundary_verts.append(v)
                    boundary_indices.append(i)
                    break
            if not is_boundary:
                interior_indices.append(i)

        num_verts = len(selected_verts)
        distances = np.zeros(num_verts)

        if not boundary_verts:
            distances[:] = 1  # 境界がない場合
        elif not interior_indices:
            distances[:] = 1  # 境界頂点しかない場合
        else:
            boundary_co = np.array([v.co for v in boundary_verts])
            interior_target_co = target_co[interior_indices]
            all_distances = np.linalg.norm(interior_target_co[:, np.newaxis] - boundary_co, axis=2)
            distances[interior_indices] = np.min(all_distances, axis=1)
            distances[boundary_indices] = 0.001

        max_distance = np.max(distances)
        if max_distance < 1e-6:
            return np.ones(len(distances))

        if self.falloff == "gaussian":
            sigma = max(max_distance / 3, 1e-4)
            weights = 1 - self.gaussian(distances, 0, sigma)
        elif self.falloff == "sphere":
            t = distances / (max_distance + 1e-6)
            weights = np.sin(t * (np.pi / 2))
        elif self.falloff == "arc":
            t = distances / (max_distance + 1e-6)
            weights = np.sin(t * (np.pi / 2))**0.75
        else:
            weights = distances / (max_distance + 1e-6)

        return np.clip(weights, 0, 1)

    @staticmethod
    def gaussian(x, mu, sigma):
        return np.exp(-((x - mu) ** 2) / (2 * sigma**2))

    def draw(self, context):
        obj = context.active_object
        layout = self.layout

        row = layout.split(factor=0.35)
        row.enabled = not self.from_history
        row.label(text="Shape")
        row.prop_search(self, "blend_source", obj.data.shape_keys, "key_blocks", text="")

        row = layout.split(factor=0.35)
        row.label(text="Subtract")
        row.prop_search(self, "blend_subtract", obj.data.shape_keys, "key_blocks", text="")

        row = layout.split(factor=0.35)
        row.label(text="Select from history")
        row.prop_search(self, "from_history", self, "select_history", icon="TOPBAR", text="")

        row = layout.split(factor=0.35)
        row.label(text="Blend")
        row.prop(self, "blend", text="")
        row = layout.split(factor=0.35)
        row.label(text="Vertex Group")
        subrow = row.row(align=True)
        subrow.prop_search(self, "blend_vertex_group", obj, "vertex_groups", text="")
        subrow.operator("wm.mio3sk_blend_set_vertex_group", icon="TRIA_LEFT", text="")
        row = layout.split(factor=0.35)
        row.label(text="Mask")
        row.prop(self, "blend_sculpt_mask", text="")
        row = layout.split(factor=0.35)
        row.label(text="")
        row.prop(self, "add")

        box = layout.box()
        
        row = box.split(factor=0.35)
        row.prop(self, "smooth")

        col = row.row()
        if not self.smooth:
            col.enabled = False
        col.prop(self, "falloff", text="")


class WM_OT_blend_set_key(Mio3SKOperator):
    bl_idname = "wm.mio3sk_blend_set_key"
    bl_label = "Set active key"
    bl_description = "Set current active key as blend source"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if obj.active_shape_key:
            context.window_manager.mio3sk.blend_source_name = obj.active_shape_key.name
        return {"FINISHED"}


class WM_OT_blend_set_subtract_key(Mio3SKOperator):
    bl_idname = "wm.mio3sk_blend_set_subtract_key"
    bl_label = "Set subtract key"
    bl_description = "Set current active key as subtract shape"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if obj.active_shape_key:
            context.window_manager.mio3sk.blend_subtract_name = obj.active_shape_key.name
        return {"FINISHED"}


class WM_OT_blend_set_vertex_group(Mio3SKOperator):
    bl_idname = "wm.mio3sk_blend_set_vertex_group"
    bl_label = "Set active vertex group"
    bl_description = "Set current active vertex group"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if obj and obj.vertex_groups.active:
            context.scene.mio3sk.blend_vertex_group = obj.vertex_groups.active.name
        return {"FINISHED"}


classes = [
    OP_PG_mio3sk_blend,
    MESH_OT_mio3sk_blend,
    WM_OT_blend_set_key,
    WM_OT_blend_set_subtract_key,
    WM_OT_blend_set_vertex_group,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
