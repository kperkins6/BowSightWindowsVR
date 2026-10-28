# Bow Sight Patcher 1.1 preview

Generate bow sight windows from your own Skyrim SE/VR mod list. No MGO dependency and no bundled game meshes.

Download **BowSightWindowsVR-1.1.0-preview-SourceToolkit.zip**, extract it, and run **Start Patcher.cmd** on Windows or `python patcher.py`. Requires **Python 3.11+** and a browser with WebGL. No extra Python packages or internet connection are needed.

- Scan an active MO2 profile or deployed game Data, including mod-added bows and compressed BSA assets.
- Choose left- or right-handed output.
- Rotate synchronized original/patched previews and adjust the shelf, height, depth, taper, bevel and individual shapes.
- Batch-select filtered meshes, transfer opening settings, inspect before/after cards, approve, include or skip.
- Save/reopen local projects and generate a separate mesh-only mod folder plus installer ZIP.
- Validate reviewed bytes and refuse stale sources, unsafe output locations or invalid geometry.

This is a preview of the standalone editor. Supported editing layouts are SSE stream-100 skinned NIFs with one partition per shape and identity bone palettes; older/unskinned or other unsupported layouts stay visible as blocked entries. Unusual bows can need manual adjustment. Neutral-shaded previews do not reproduce the game's shaders, animated draw pose or headset view.

Install generated output through your mod manager after reviewing it. The tool does not change or enable your installed mods. Keep your source mods and textures installed. Saved projects and generated manifests contain local source paths and should stay local.

The original 1.0 reference FOMOD builder remains included. Redistribution permissions for third-party meshes remain separate from the MIT license on the tools.
