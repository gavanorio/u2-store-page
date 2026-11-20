# Livery and artwork renders

Scripts that made the pictures `files/u2s_liv_*.webp` and `files/u2s_artw_*.webp` (2026-11-20).

1. `prep_gltf.py`: patches the exterior LOD0 glTF files of the aircraft project (in-flight pose, texture paths).
2. `build_scene.py`: imports them into one Blender scene (`bpy` 5.3).
3. `final.py <livery> [picture]`: sets the livery textures and the aircraft configuration from the model XML visibility rules, then renders with Cycles.

Configuration: ASARS-2 nose, SPAN antenna, Type A superpods, gear up. Exceptions: 68-10329 Hawk has the standard nose, 80-1067 has the SYERS-2A nose and shows the right side.
Side views: 1395 x 510 px, grey background. Artwork: 1300 x 470 px, white background. Renders are made at 2x and scaled down.
The paths in the scripts are those of the render workspace. Change them before you use the scripts again.
