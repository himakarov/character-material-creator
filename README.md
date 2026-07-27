# Character Material Tool

Auto-builds Karma materials for characters in Houdini (Solaris).
Walks a folder of per-material subfolders, builds MaterialX graphs, and
assigns them to meshes and GeomSubsets.

## Install

1. Download latest version from the [latest Release](../../releases/latest).
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
           └── toolbar/
   ```
   No renaming needed - the zip is already laid out correctly.
4. Restart Houdini. A **Char Mat Tool** shelf tab appears.

## Usage

1. Build your character in `/stage` (e.g. via SOP Import with a skeleton) and
   set the display flag on the node you want.
2. Click **Char Mat** on the shelf.
3. Pick the folder with per-material subfolders (each subfolder = one material,
   containing textures with suffixes `_basecolor`, `_normal`, `_roughness`,
   `_metallic`).
4. Click **Build**.

## Updating

The **Check for updates** button pulls the latest version from GitHub. If a
newer version exists it downloads and overwrites the local files. Restart
Houdini after updating. The **Changelog** button shows what changed.
REPO_SUBDIR = "CharacterMaterialTool"
```
To publish an update: bump the number in `VERSION`, add a `CHANGELOG.md` entry,
and push to the repository.
