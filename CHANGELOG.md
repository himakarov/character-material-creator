# Changelog

## 1.1.0
- Shared shelf: the tool now registers its button into a single "CGA Tools"
  shelf instead of creating its own tab. Future CGA tools can share the same
  shelf, so you get one tab with many buttons instead of one tab per tool.
- The updater now also refreshes the package manifest (character_mat_tool.json)
  in packages/, so manifest changes ship through the Update button too.

## 1.0.3
- UI: proper update button styling; custom shelf icon.

## 1.0.2
- Support FBX-via-SOP imports (ancestry name resolution); ignore mesh_N names
  when computing the character prefix.

## 1.0.1
- Fixed assignment when subsets are named after a shader path.

## 1.0.0
- Initial release.
