# Character Material Tool

Auto-builds Karma materials for characters in Houdini (Solaris).
Walks a folder of per-material subfolders, builds MaterialX graphs, and
assigns them to meshes and GeomSubsets.

## Install

1. Download the repository (GitHub **Code -> Download ZIP**) and unzip it.
2. Locate your Houdini user preferences folder:
   - Windows: `C:/Users/<name>/Documents/houdini20.5/`
   - macOS: `~/Library/Preferences/houdini/20.5/`
   - Linux: `~/houdini20.5/`
   (use your actual version)
3. Create a `packages` folder inside it if it does not exist.
4. Copy the **file** `character_mat_tool.json` and the **folder**
   `CharacterMaterialTool` there, so you get:
   ```
   houdini20.5/
   └── packages/
       ├── character_mat_tool.json
       └── CharacterMaterialTool/
           ├── VERSION
           ├── python/
           └── toolbar/
   ```
5. Restart Houdini. A **Char Mat Tool** shelf tab appears.

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

## Maintainer setup

In `python/character_mat_tool/updater.py` set:
```python
GITHUB_USER = "your_login"
GITHUB_REPO = "your_repo"
GITHUB_BRANCH = "main"
REPO_SUBDIR = "CharacterMaterialTool"
```
To publish an update: bump the number in `VERSION`, add a `CHANGELOG.md` entry,
and push to the repository.
