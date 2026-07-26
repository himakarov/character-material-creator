# Changelog

## 1.0.2
- Support FBX-via-SOP imports in addition to clean USDC references.
  The tool now resolves material names by walking up the prim ancestry,
  so it works whether subsets are named cleanly (USDC) or after a shader
  path (FBX), and whether meshes carry the real name or an auto-name like
  mesh_0 (real name on the parent Xform).
- Ignore auto-named prims (mesh_N, geoN) when computing the character
  prefix, fixing broken matching when teeth/eyes come in as mesh_0.

## 1.0.1
- Fixed material assignment when GeomSubsets are named after a full shader
  path. Falls back to the parent mesh name.

## 1.0.0
- Initial release.
- Auto-build Karma MaterialX materials from per-material subfolders.
- Core-based name matching.
- Assign to meshes and GeomSubsets.
- Self-update from GitHub over HTTP.
