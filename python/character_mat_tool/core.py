"""
core.py - Karma material build logic for characters.
UI-independent; called from ui.py.
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


# ---------------------------------------------------------------------------
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


def _collect_geo(matlib):
    # items: (path, type, name, parent_mesh_name)
    # parent_mesh_name is used as a fallback when a subset name is garbage
    # (e.g. imports that name subsets after a full shader path).
    items = []
    try:
        stage = matlib.stage()
        mesh_names = {}   # mesh path -> mesh short name
        with_subsets = set()
        for p in stage.Traverse():
            if p.GetTypeName() == "Mesh":
                mesh_names[str(p.GetPath())] = p.GetName()
        for p in stage.Traverse():
            if p.GetTypeName() == "GeomSubset":
                path = str(p.GetPath())
                parent = path.rsplit("/", 1)[0]
                items.append((path, "subset", p.GetName(),
                              mesh_names.get(parent, "")))
                with_subsets.add(parent)
        for path, mname in mesh_names.items():
            if path in with_subsets:
                continue
            items.append((path, "mesh", mname, ""))
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
        # backward-compatible unpack (subset items carry a parent mesh name)
        path, gtype, sname = item[0], item[1], item[2]
        parent_mesh = item[3] if len(item) > 3 else ""
        mat = None
        if gtype == "subset":
            if sname in created_set:
                mat = sname
            else:
                mat = _find_mat(_core_of_material(sname, mat_prefix))
            # fallback: subset name is garbage (e.g. a shader path) ->
            # use the parent mesh name to find the material
            if not mat and parent_mesh:
                mat = _find_mat(_core_of_mesh(parent_mesh, char_prefix))
        else:
            if MATCH_MODE == "suffix":
                cand = sname + MAT_SUFFIX
                if cand in created_set:
                    mat = cand
            else:
                mat = _find_mat(_core_of_mesh(sname, char_prefix))
        if mat:
            pairs.append((path, mat))
        else:
            unmatched.append(sname)
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
    assign.setDisplayFlag(True)
    assign.setSelected(True, clear_all_selected=True)
    return assign


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
    matlib = stage.createNode("materiallibrary")
    matlib.setName(matlib_name, unique_name=True)

    try:
        disp = stage.displayNode()
        if disp is not None and disp.path() != matlib.path():
            matlib.setInput(0, disp)
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
    if assign and created:
        geo_items = _collect_geo(matlib)
        # prefix from every mesh name: standalone meshes (item type "mesh")
        # and parent meshes of subsets (4th element)
        mesh_names = [it[2] for it in geo_items if it[1] == "mesh"]
        mesh_names += [it[3] for it in geo_items
                       if it[1] == "subset" and len(it) > 3 and it[3]]
        char_prefix = _common_prefix(mesh_names) if mesh_names else mat_prefix
        pairs, unmatched = _match_pairs(geo_items, created, char_prefix, mat_prefix)
        _assign_materials(stage, matlib, pairs, mat_prefix)
        assigned = len(pairs)

    return {
        "created": created,
        "skipped": skipped,
        "assigned": assigned,
        "unmatched": sorted(set(unmatched)),
        "matlib": matlib.path(),
    }
