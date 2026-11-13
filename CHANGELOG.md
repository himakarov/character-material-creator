# Changelog

## 1.2.1
- Fixed Build resetting materials on other assets in the scene. The
  `fbx_material_name` partition retarget ran on every SOP Import / SOP Create
  in `/stage`, so a location or prop partitioned by `shop_materialpath` lost
  its GeomSubsets and its assigned materials. It now only touches the selected
  character node and the nodes upstream of it, and skips any node whose
  geometry has no `fbx_material_name` attribute.

## 1.2.0
- Handle the "split slot" case: one mesh carrying several source materials
  (e.g. one FBX-merged shop_materialpath covering two real materials).
  SOP Import LOPs are retargeted to partition GeomSubsets by
  `fbx_material_name` so each material gets its own subset, subset names are
  matched back to exact material names, and meshes that can't be split on
  import (baked Reference/USDC without `fbx_material_name`) are now reported
  with a clear warning instead of silently misassigning.
- New nodes (material library, assign material) are now chained directly
  below the character node selected in `/stage` before Build is pressed,
  instead of guessing from the display flag.

## 1.1.3
- Fixed the updater: it had placeholder repo settings (YOUR_USERNAME/YOUR_REPO)
  and a wrong subdir, so "Check for updates" always failed with a connection
  error. Now points at the real repository, so self-update works.

## 1.1.2
- Fixed material assignment (0 assigned) for characters with indexed meshes
  like Teeth_0/1/2 collapsing the character prefix.

## 1.1.1
- Reliable startup shelf registration via scripts/python/ready.py.

## 1.1.0
- Shared "CGA Tools" shelf; updater refreshes the manifest.

## 1.0.3
- UI: update button styling; custom shelf icon.

## 1.0.2
- Support FBX-via-SOP imports (ancestry name resolution).

## 1.0.1
- Fixed assignment for shader-path-named subsets.

## 1.0.0
- Initial release.
