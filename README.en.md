# Character Material Tool

[Русский](README.md) | [English](README.en.md)

Auto-builds Karma materials for characters in Houdini (Solaris).
Walks a folder of per-material subfolders, builds MaterialX graphs, and
assigns them to meshes and GeomSubsets.

The tool handles the common case where a single mesh carries several source
materials (e.g. one body mesh split into two material slots). See
[How material splitting works](#how-material-splitting-works) below.

## Install

1. Download the latest version from the [latest Release](../../releases/latest).
2. Locate your Houdini user preferences folder and the `packages` folder
   inside it (create `packages` if it does not exist yet):
   - Windows: `C:/Users/<name>/Documents/houdini22.0/packages/`
   - macOS: `~/Library/Preferences/houdini/22.0/packages/`
   - Linux: `~/houdini22.0/packages/`
   (use your actual version)
3. Extract the zip directly into that `packages` folder, so you get:
   ```
   houdini22.0/
   └── packages/
       ├── character_mat_tool.json
       └── CharacterMaterialTool/
           ├── VERSION
           ├── python/
           ├── config/
           └── scripts/
   ```
   No renaming needed - the zip is already laid out correctly.
4. Restart Houdini. A **CGA Tools** shelf tab appears with a **Char Mat** button.

## Usage

1. Build your character in `/stage`. Either route works:
   - **SOP Import** (SOP Create / SOP Import UsdSkel Character) fed by an
     FBX Character Import, or
   - **Reference / Payload** of a baked `.usdc`.
2. **Select the character node** you want to assign materials to (the SOP
   Import or the Reference node). The tool chains its new nodes directly below
   the selected node, so selection is required - if nothing in `/stage` is
   selected, Build stops and asks you to select the character node.
3. Click **Char Mat** on the shelf.
4. Pick the folder with per-material subfolders (each subfolder = one material,
   containing textures with suffixes `_basecolor`, `_normal`, `_roughness`,
   `_metallic`).
5. Click **Build**.

The tool adds two nodes in a chain below your character:
```
<your character node>
        │
  materiallibrary   (builds the MaterialX graphs)
        │
  assignmaterial    (binds materials to meshes / subsets)
```

## How material splitting works

FBX Character Import can merge several material slots of one mesh into a single
`shop_materialpath`. By default SOP Import slices GeomSubsets by
`shop_materialpath`, so a merged mesh ends up with **one** subset and the extra
materials have nowhere to bind. The tool resolves this per input type:

- **SOP input.** Before building, the tool retargets the SOP Import partition
  to `fbx_material_name` (and enables *Prefix Subsets with Attribute Name*).
  This natively slices one GeomSubset per real material, so a merged mesh gets
  a separate subset for each of its material slots automatically. No extra
  utility nodes, and the change survives undo.

- **Reference / baked USD input.** A baked `.usdc` has no `fbx_material_name`,
  so it cannot be re-partitioned on import - the split has to exist in the file
  already. If the USD was exported with **Subset Attributes = `fbx_material_name`**,
  the subsets are already correct and everything binds as expected. If it was
  exported with a merged subset, the tool cannot split it and instead reports
  the affected mesh, e.g.:
  ```
  <MeshName>: 1 subset but 2 candidate materials
  (<MaterialA>, <MaterialB>).
  Re-export this asset's USD with 'Subset Attributes = fbx_material_name'.
  ```
  Re-export the character's USD with that setting and the mesh will bind
  correctly.

**Recommended export setting:** when writing character USDs, set
**Subset Attributes = `fbx_material_name`** (with *Prefix Subsets with Attribute
Name* on). This keeps per-slot splits intact and makes both SOP and Reference
workflows behave identically.

## Material matching

Meshes and subsets are matched to materials by name:

- A GeomSubset whose auto-generated name carries the material
  (`fbx_material_name_<MatName>`) binds directly to that material.
- Otherwise the mesh / subset name is matched to a material by common core
  name: the character prefix is stripped from the mesh and the prefix +
  suffixes (`_Mat`, `_M`, `_Material`) are stripped from the material, then the
  remainders are compared (e.g. `<Prefix>_Arms` ↔ `<Prefix>_ArmsMat` → `arms`).

Anything the tool could not match is listed in the Build report so you can spot
naming mismatches or missing texture folders.

## Updating

The **Check for updates** button pulls the latest version from GitHub. If a
newer version exists it downloads and overwrites the local files. Restart
Houdini after updating. The **Changelog** button shows what changed.
