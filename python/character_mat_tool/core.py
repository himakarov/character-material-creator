"""
core.py - Karma material build logic for characters.
UI-independent; called from ui.py.

v1.2.0
------
Handles the "split slot" case: one mesh carrying several source materials
(e.g. T_Adam_Overalls -> OverallsPantsMat + OverallsShirtMat, or
CT_Warden_Suit -> JacketMat + PantsMat).

Root cause of the old failure: FBX Character Import merges several material
slots into ONE shop_materialpath, so SOP Import LOP (which partitions
GeomSubsets by shop_materialpath) produces a SINGLE subset for the whole mesh
and the second material has nowhere to bind.

Fix strategy (in order of preference):
  1. SOP input  -> retarget SOP Import partition to `fbx_material_name`
     (enable_partitionattribs + partitionattribs). This natively slices one
     GeomSubset per real material. No extra nodes, survives undo.
  2. Matching    -> subset names then look like `fbx_material_name_<MatName>`
     (or legacy `shop_materialpath__materials_<MatName>`); we extract the exact
     material name from the subset name and bind precisely.
  3. Reference input (baked .usdc) -> cannot be repartitioned on import
     (no fbx_material_name in the file). If a mesh has one subset but several
     candidate materials, we report it clearly so the USD can be re-exported
     with `Subset Attributes = fbx_material_name` (as Warden USD was).
"""

import os
import hou

# ---------------------------------------------------------------------------
# CONFIG (defaults; UI may override)
# ---------------------------------------------------------------------------
SUFFIX_MAP = {
    "basecolor": "base_color",
    "roughness": "specular_roughness",
    "metallic":  "metalness",
    "normal":    "normal",
}
RAW_INPUTS = {"specular_roughness", "metalness", "normal"}
COLOR_INPUTS = {"base_color"}
TEXTURE_EXTS = (".tif", ".tiff", ".png", ".exr", ".jpg", ".jpeg", ".tga")

MATCH_MODE = "core"          # "core" | "suffix"
MAT_SUFFIX = "Mat"
MAT_NAME_SUFFIXES = ["_Mat", "_M", "Mat", "_Material"]
MATERIALS_PREFIX = "/materials/"

# Attribute we want SOP Import LOPs to partition GeomSubsets by.
# fbx_material_name preserves per-slot splits that shop_materialpath collapses.
PARTITION_ATTRIB = "fbx_material_name"

# Subset-name prefixes Houdini emits when "Prefix Subsets with Attribute Name"
# is on. Used to recover the exact material name from an auto-generated subset.
SUBSET_NAME_PREFIXES = ["fbx_material_name_"]


# ---------------------------------------------------------------------------
def _strip_trailing_index(name):
    """Remove a trailing _N index so Teeth_0/Teeth_1 share a common prefix.
    Runner_A_Teeth_0 -> Runner_A_Teeth."""
    import re as _re
    return _re.sub(r"_\d+$", "", name)


def _common_prefix(names):
    if not names:
        return ""
    pref = os.path.commonprefix(names)
    if "_" in pref:
        pref = pref.rsplit("_", 1)[0]
    return pref.strip("_")


def _strip_suffixes(name, suffixes):
    low = name.lower()
    for suf in suffixes:
        if low.endswith(suf.lower()):
            return name[: len(name) - len(suf)]
    return name


def _core_of_mesh(mesh_name, char_prefix):
    core = mesh_name
    if char_prefix and core.lower().startswith(char_prefix.lower()):
        core = core[len(char_prefix):]
    return core.strip("_").lower()


def _core_of_material(mat_name, mat_prefix):
    core = mat_name
    if mat_prefix and core.lower().startswith(mat_prefix.lower()):
        core = core[len(mat_prefix):]
    core = _strip_suffixes(core.strip("_"), MAT_NAME_SUFFIXES)
    return core.strip("_").lower()


def _find_textures(folder):
    found = {}
    for fname in os.listdir(folder):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in TEXTURE_EXTS:
            continue
        low = stem.lower()
        for suffix_key in SUFFIX_MAP:
            if low.endswith("_" + suffix_key) or low.endswith(suffix_key):
                found[suffix_key] = os.path.join(folder, fname)
                break
    return found


def _set_parm(node, names, value):
    for n in names:
        p = node.parm(n)
        if p is not None:
            try:
                p.set(value)
                return True
            except Exception:
                pass
    return False


def _build_material(matlib, mat_name, textures):
    sub = matlib.createNode("subnet", mat_name)
    out = sub.createNode("subnetconnector", "surface_output")
    out.parm("connectorkind").set("output")
    out.parm("parmname").set("surface")
    out.parm("parmlabel").set("Surface")
    _set_parm(out, ["parmtype"], "surface")

    surface = sub.createNode("mtlxstandard_surface", "mtlxstandard_surface")
    out.setInput(0, surface)

    for suffix_key, filepath in textures.items():
        target_input = SUFFIX_MAP[suffix_key]
        is_raw = target_input in RAW_INPUTS
        img = sub.createNode("mtlximage", "img_" + suffix_key)
        img.parm("file").set(filepath.replace("\\", "/"))

        if suffix_key == "normal":
            _set_parm(img, ["signature"], "vector3")
            _set_parm(img, ["filecolorspace", "colorspace"], "Raw")
            nmap = sub.createNode("mtlxnormalmap", "normalmap")
            nmap.setInput(0, img)
            surface.setNamedInput("normal", nmap, 0)
        else:
            sig = "color3" if target_input in COLOR_INPUTS else "float"
            _set_parm(img, ["signature"], sig)
            _set_parm(img, ["filecolorspace", "colorspace"],
                      "Raw" if is_raw else "srgb_texture")
            surface.setNamedInput(target_input, img, 0)

    try:
        sub.setMaterialFlag(True)
    except Exception:
        pass
    sub.layoutChildren()
    return sub


def _is_garbage_name(name):
    """True if a prim name carries no material info."""
    if not name:
        return True
    low = name.lower()
    if low.startswith("shop_materialpath"):
        return True
    if low.startswith("principledshader") or "principledshader" in low:
        return True
    # generic auto-names like mesh_0, mesh_1, geo1, object_3
    import re as _re
    if _re.match(r"^(mesh|geo|object|prim)_?\d+$", low):
        return True
    return False


def _mat_from_subset_name(sname):
    """Recover the exact material name baked into an auto-generated GeomSubset
    name. Supports:
        fbx_material_name_<MatName>              (partition by fbx_material_name)
        shop_materialpath__materials_<MatName>   (legacy wrangle-split path)
    Returns '' for anything else (garbage shader-path subsets, clean mesh
    names, etc.) so callers can safely fall through to the old matching
    branches. Strict on purpose: no greedy '__' fallback that could misfire
    on characters whose subsets were already clean (e.g. Warden USD)."""
    if not sname:
        return ""
    for pref in SUBSET_NAME_PREFIXES:
        if sname.startswith(pref):
            return sname[len(pref):]
    marker = "_materials_"
    idx = sname.rfind(marker)
    if idx != -1:
        return sname[idx + len(marker):]
    return ""


def _meaningful_name(prim):
    """Walk up the prim's ancestry and return the first non-garbage name.
    Handles: clean subset/mesh names, mesh_N with the real name on the parent
    Xform, and shader-path subset names."""
    node = prim
    depth = 0
    while node is not None and depth < 4:
        try:
            nm = node.GetName()
        except Exception:
            nm = ""
        if not _is_garbage_name(nm):
            return nm
        try:
            node = node.GetParent()
        except Exception:
            break
        depth += 1
    return ""


def _collect_geo(matlib):
    # items: (path, type, name, resolved_name)
    # resolved_name is the best material-bearing name found by walking up
    # the ancestry (covers USDC clean names AND FBX-via-SOP messy names).
    items = []
    try:
        stage = matlib.stage()
        with_subsets = set()
        for p in stage.Traverse():
            if p.GetTypeName() == "GeomSubset":
                path = str(p.GetPath())
                parent = path.rsplit("/", 1)[0]
                items.append((path, "subset", p.GetName(), _meaningful_name(p)))
                with_subsets.add(parent)
        for p in stage.Traverse():
            if p.GetTypeName() != "Mesh":
                continue
            path = str(p.GetPath())
            if path in with_subsets:
                continue
            items.append((path, "mesh", p.GetName(), _meaningful_name(p)))
    except Exception:
        pass
    return items


def _match_pairs(geo_items, created_names, char_prefix, mat_prefix):
    created_set = set(created_names)
    mat_by_core = {}
    for m in created_names:
        mat_by_core[_core_of_material(m, mat_prefix)] = m

    core_list = [(_core_of_material(m, mat_prefix), m) for m in created_names]

    def _find_mat(core):
        if core in mat_by_core:
            return mat_by_core[core]
        best, best_len = None, 0
        for mcore, mname in core_list:
            if not core or not mcore:
                continue
            if mcore.startswith(core) or core.startswith(mcore):
                ov = min(len(mcore), len(core))
                if ov > best_len:
                    best_len, best = ov, mname
        return best

    pairs, unmatched = [], []
    for item in geo_items:
        path, gtype, sname = item[0], item[1], item[2]
        resolved = item[3] if len(item) > 3 else ""
        mat = None

        # 0. subset name carries the exact material name
        #    (fbx_material_name_<MatName> or legacy _materials_<MatName>).
        #    Runs BEFORE the garbage check so split-slot subsets (Shirt vs
        #    Pants on one mesh) resolve to distinct materials instead of
        #    collapsing to the shared parent mesh name. Strict extractor
        #    returns '' for clean/garbage names, so nothing else is affected.
        if gtype == "subset":
            embedded = _mat_from_subset_name(sname)
            if embedded:
                if embedded in created_set:
                    mat = embedded
                else:
                    mat = _find_mat(_core_of_material(embedded, mat_prefix))

        # 1. exact subset name == material name (clean USDC pipeline)
        if not mat and gtype == "subset" and sname in created_set:
            mat = sname
        # 2. subset name resolved via core matching
        if not mat and gtype == "subset" and not _is_garbage_name(sname):
            mat = _find_mat(_core_of_material(sname, mat_prefix))
        # 3. resolved ancestry name (covers messy FBX subsets and mesh_N)
        if not mat and resolved:
            mat = _find_mat(_core_of_mesh(resolved, char_prefix))
        # 4. suffix mode on the mesh's own name
        if not mat and gtype == "mesh":
            if MATCH_MODE == "suffix":
                cand = sname + MAT_SUFFIX
                if cand in created_set:
                    mat = cand
            elif not _is_garbage_name(sname):
                mat = _find_mat(_core_of_mesh(sname, char_prefix))

        if mat:
            pairs.append((path, mat))
        else:
            unmatched.append(resolved or sname)
    return pairs, unmatched


def _assign_materials(stage_node, matlib, pairs, prefix=""):
    if not pairs:
        return None
    assign = stage_node.createNode("assignmaterial")
    if prefix:
        assign.setName(prefix + "_assignmaterial", unique_name=True)
    assign.setInput(0, matlib)
    _set_parm(assign, ["nummaterials"], len(pairs))
    for i, (geo_path, mat_name) in enumerate(pairs, 1):
        _set_parm(assign, ["primpattern%d" % i, "geopath%d" % i], geo_path)
        _set_parm(assign, ["matspecpath%d" % i, "materialpath%d" % i,
                           "matpath%d" % i], MATERIALS_PREFIX + mat_name)
    # place assign directly below matlib (only setPosition on the new node)
    try:
        mp = matlib.position()
        assign.setPosition(hou.Vector2(mp.x(), mp.y() - 1.0))
    except Exception:
        pass
    assign.setDisplayFlag(True)
    assign.setSelected(True, clear_all_selected=True)
    return assign


# ---------------------------------------------------------------------------
# Split-slot handling
# ---------------------------------------------------------------------------
def _sop_geometry_has_attrib(node, attrib_name):
    """Whether the SOP geometry a SOP Import / SOP Create LOP brings in has
    the primitive attribute. Returns None when the geometry can't be read."""
    try:
        if node.type().name().startswith("sopcreate"):
            sop = node.node("sopnet/create").displayNode()
        else:
            sop = node.parm("soppath").evalAsNode()
        geo = sop.geometry()
        return geo.findPrimAttrib(attrib_name) is not None
    except Exception:
        return None


def _retarget_sop_partitions(anchor):
    """Find SOP Import LOPs feeding the character (the anchor node and
    everything upstream of it) and make them partition GeomSubsets by
    PARTITION_ATTRIB (fbx_material_name) instead of shop_materialpath.

    This natively slices one GeomSubset per real material, fixing merged-slot
    meshes for any SOP-fed character. Idempotent: skips nodes already set
    correctly. Only touches nodes that actually expose the partition parms
    (SOP Import / SOP Create), so Reference LOPs are ignored.

    Nodes on other branches of /stage (a location, props) are left alone, and
    so is any node whose geometry has no fbx_material_name attribute:
    retargeting those would remove their shop_materialpath subsets and with
    them the materials already assigned there.

    Returns a list of node paths that were changed (for reporting)."""
    changed = []
    if anchor is None:
        return changed

    for node in [anchor] + list(anchor.inputAncestors()):
        pa = node.parm("partitionattribs")
        en = node.parm("enable_partitionattribs")
        if pa is None or en is None:
            continue  # not a SOP Import LOP
        if _sop_geometry_has_attrib(node, PARTITION_ATTRIB) is False:
            continue  # nothing to partition by; keep its current subsets

        current = pa.eval()
        need = (en.eval() != 1) or (PARTITION_ATTRIB not in current.split())
        if not need:
            continue

        try:
            en.set(1)
            # keep any existing attribs the user may rely on, drop the merged
            # shop_materialpath, ensure ours is present
            existing = [a for a in current.split()
                        if a and a != "shop_materialpath"]
            if PARTITION_ATTRIB not in existing:
                existing.append(PARTITION_ATTRIB)
            pa.set(" ".join(existing) if existing else PARTITION_ATTRIB)
            # prefix subset names with the attribute name -> stable extraction
            _set_parm(node, ["enable_prefixpartitionsubsets"], 1)
            _set_parm(node, ["prefixpartitionsubsets"], 1)
            changed.append(node.path())
        except Exception:
            pass

    return changed


def _detect_unsplittable(matlib, created_names, mat_prefix):
    """Detect meshes that carry a SINGLE subset but map to SEVERAL candidate
    materials (the merged-slot case that cannot be fixed on import, e.g. a
    baked Reference/USDC without fbx_material_name).

    Returns a list of human-readable warnings for the report."""
    warnings = []
    try:
        stage = matlib.stage()
    except Exception:
        return warnings

    created_cores = {}
    for m in created_names:
        created_cores.setdefault(_core_of_material(m, mat_prefix), []).append(m)

    for prim in stage.Traverse():
        if prim.GetTypeName() != "Mesh":
            continue
        subs = [c for c in prim.GetChildren()
                if c.GetTypeName() == "GeomSubset"]
        if len(subs) != 1:
            continue  # 0 subsets or already split -> not this case

        mesh_name = prim.GetName()
        mesh_core = _core_of_mesh(mesh_name, mat_prefix)

        # how many created materials look like they belong to this mesh?
        candidates = []
        for mcore, mats in created_cores.items():
            if not mesh_core or not mcore:
                continue
            if mcore.startswith(mesh_core) and mcore != mesh_core:
                candidates.extend(mats)

        if len(candidates) >= 2:
            warnings.append(
                "%s: 1 subset but %d candidate materials (%s). "
                "Re-export this asset's USD with "
                "'Subset Attributes = fbx_material_name'."
                % (mesh_name, len(candidates), ", ".join(sorted(candidates)))
            )
    return warnings


def build(root_folder, assign=True):
    """Main entry. root_folder - folder with per-material subfolders.
    Returns a stats dict for the UI."""
    root = hou.text.expandString(root_folder).rstrip("/\\")
    if not os.path.isdir(root):
        return {"error": "Not a folder: %s" % root}

    subfolders = [d for d in sorted(os.listdir(root))
                  if os.path.isdir(os.path.join(root, d))]
    if not subfolders:
        return {"error": "No material subfolders found"}

    mat_prefix = _common_prefix(subfolders)
    matlib_name = (mat_prefix + "_materiallibrary") if mat_prefix else "materiallibrary_auto"

    stage = hou.node("/stage")

    # Anchor = the character node the user selected before pressing Build.
    # New nodes are chained below it: anchor -> materiallibrary -> assignmaterial.
    sel = hou.selectedNodes()
    anchor = None
    for n in sel:
        # take the first selected node that lives in /stage
        try:
            if n.parent() is not None and n.parent().path() == "/stage":
                anchor = n
                break
        except Exception:
            continue
    if anchor is None:
        return {"error": "Select the character node in /stage before building "
                         "(the SOP Import or Reference node)."}

    # --- STEP 0: make SOP Import LOPs partition by fbx_material_name so
    #     merged-slot meshes get one GeomSubset per real material.
    #     (No-op for Reference-only setups; those are diagnosed later.)
    partition_changed = _retarget_sop_partitions(anchor)

    matlib = stage.createNode("materiallibrary")
    matlib.setName(matlib_name, unique_name=True)

    # chain matlib below the anchor and position it (setPosition only on the
    # new node - never layoutChildren on the parent, it destroys the graph).
    try:
        matlib.setInput(0, anchor)
        ap = anchor.position()
        matlib.setPosition(hou.Vector2(ap.x(), ap.y() - 1.0))
    except Exception:
        pass

    created, skipped = [], []
    for sub in subfolders:
        textures = _find_textures(os.path.join(root, sub))
        if not textures:
            skipped.append(sub)
            continue
        _build_material(matlib, sub, textures)
        created.append(sub)

    matlib.layoutChildren()
    matlib.setDisplayFlag(True)
    for pname in ("fillmaterials", "auto_fill", "fillmaterialflag"):
        p = matlib.parm(pname)
        if p is not None:
            try:
                p.pressButton()
                break
            except Exception:
                pass

    assigned, unmatched = 0, []
    split_warnings = []
    if assign and created:
        geo_items = _collect_geo(matlib)
        # Build a name pool for prefix detection, stripping trailing numeric
        # parts (Runner_A_Teeth_0/1/2 would otherwise collapse the common
        # prefix to nothing).
        name_pool = []
        for it in geo_items:
            for nm in (it[3] if len(it) > 3 else "", it[2]):
                if nm and not _is_garbage_name(nm):
                    name_pool.append(_strip_trailing_index(nm))
        char_prefix = _common_prefix(name_pool) if name_pool else ""

        # If prefix detection failed or is weaker than the material prefix,
        # fall back to the material prefix (they match for a character).
        if len(char_prefix) < len(mat_prefix):
            char_prefix = mat_prefix

        pairs, unmatched = _match_pairs(geo_items, created, char_prefix, mat_prefix)
        _assign_materials(stage, matlib, pairs, mat_prefix)
        assigned = len(pairs)

        # Diagnose meshes that couldn't be split on import (baked references).
        split_warnings = _detect_unsplittable(matlib, created, mat_prefix)

    return {
        "created": created,
        "skipped": skipped,
        "assigned": assigned,
        "unmatched": sorted(set(unmatched)),
        "matlib": matlib.path(),
        "partition_changed": partition_changed,
        "split_warnings": split_warnings,
    }
