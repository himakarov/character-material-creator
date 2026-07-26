# Changelog

## 1.0.1
- Fixed material assignment when GeomSubsets are named after a full shader
  path (imports without a clean fbx_material_name partition). The tool now
  falls back to the parent mesh name to resolve the material.

## 1.0.0
- Initial release.
- Auto-build Karma MaterialX materials from per-material subfolders.
- Core-based name matching (handles differing mesh/material prefixes and
  FBX-truncated names).
- Assign to meshes and GeomSubsets.
- Self-update from GitHub over HTTP.
