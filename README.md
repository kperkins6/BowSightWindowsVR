# Bow Sight Windows VR

Create sight windows for bows from your own Skyrim SE/VR mod list: an arrow shelf and a narrower section above the grip for a clearer view along the arrow.

## Standalone patcher

The new local patcher discovers the bows in your own mod list, previews actual before/after geometry, lets you adjust each opening, and generates a separate output mod. It supports left/right handedness, per-shape controls, saved projects, and **batch selection with preview cards and batch approval**. It does not require MGO or distribute anyone else's meshes.

[Download the standalone patcher source package](https://github.com/kperkins6/BowSightWindowsVR/releases/tag/v1.1.1-preview), extract it, and run **Start Patcher.cmd** on Windows, or `python patcher.py` with Python 3.11+. No extra Python packages or internet connection are needed.

**Most users can use the three steps at the top of the page:**

1. **Find bows** in an MO2 profile or deployed game Data.
2. Choose your hand and **Build all supported with defaults**.
3. Choose an output folder and **Approve successful & generate mod**.

Failed defaults and unsupported meshes are listed separately and excluded automatically. No per-bow review is required. Individual 3D editing and manual batch controls remain available in an optional section. [Patcher guide and supported layouts](docs/PATCHER.md).

The reference 1.0 FOMOD builder below remains available separately.

![Bow without a sight window and bow with a sight window](docs/images/iron-bow-comparison.png)

**Public downloads contain the patcher, source and documentation only.** Meshes are generated locally from your installed assets. No game files or modified third-party NIFs are stored in this repository or attached to its releases. The separate reference mesh archive remains local while upstream redistribution permissions are reviewed.

## What the mod changes

- A cutout beginning beneath the existing drawn-arrow position, with a thinner section above it.
- Left-handed: bow in the **right** hand, string drawn with the **left**.
- Right-handed: bow in the **left** hand, string drawn with the **right**.
- Vanilla Skyrim, Dawnguard and Dragonborn bow families, Bound Bow, Drainspell Bow and unique-model variants used by the reference setup: **34 mesh paths per hand**.

The mod installs meshes only. It keeps the source skeletons, grip and arrow placement, collision, animation references, materials and original vertex weights. It does not change aiming, draw speed, damage, ballistics, or Bow Inertia VR code/settings. A global mesh choice also affects NPC/world appearances that share those models.

## Scope and compatibility

This reference build was made against an existing **MGO setup**, using Cathedral Armory, Vanilla Weapon Replacer SSE, PGPatcher output and some Legacy of the Dragonborn unique models. It is not a standalone replacement for every possible vanilla/replacer installation. Keep the matching textures and materials. Crossbows and NPC-only dummy bows are excluded. The pictured `ironbow.nif` is the Imperial Bow model in the game records.

The reference FOMOD builder accepts the exact source hashes in [reference_sources.json](reference_sources.json). The standalone patcher accepts other sources within its [supported NIF layouts](docs/PATCHER.md#supported-layouts-and-limitations); unusual geometry needs visual adjustment and review.

## Build a local FOMOD

Use Python 3.10 or later. The core builder uses only the standard library.

1. Obtain the source mods through their original distribution pages and keep them installed locally.
2. Assemble an untouched source folder whose contents match the relative paths and SHA-256 values in `reference_sources.json`. Paths are relative to `meshes/`; do not use this sight-window mod's already-modified NIFs as inputs. Unique files packed in BSAs need to be extracted locally with your preferred asset tool.
3. Run:

```powershell
python tools/build.py --source-dir "D:/Modding/BowSources" --output-dir "D:/Modding/BowSightWindowsBuild"
```

The builder generates 68 meshes, checks every result against the verified 1.0 output hashes, and creates a local `BowSightWindows-VanillaDLC-MGO-1.0.0-FOMOD.zip`. It does not modify MO2, a game installation, or the source folder. Source and output folders must be separate and non-nested.

Install that locally generated ZIP through MO2, choose one handedness, and let it win conflicts with the source bow meshes/PGPatcher output. Reinstall and replace to switch hands; disable the mod to restore the underlying meshes.

## Verification

All 68 reference outputs passed offline checks for valid geometry and bounds, preserved original UVs/weights, unchanged skeleton/material/collision blocks and exclusive FOMOD routing. In-game feedback informed the left-handed design; right-handed placement and all live effect combinations have not been exhaustively headset-tested.

Bound Bow's flame/refraction surfaces follow the opening. Newly added effect vertices use the engine's four-influence limit; the largest discarded interpolation influence is approximately 6.42%, confined to new effect-sheet vertices. Original weights remain untouched.

Run the source-only tests with:

```powershell
python -m unittest discover -s tests -v
```

## Nexus preparation and credits

[Nexus draft and upload checklist](docs/nexus/README.md) · [BBCode description](docs/nexus/description.bbcode) · [Credits and asset permissions](docs/ASSET_PERMISSIONS.md) · [Changelog](CHANGELOG.md)

The original tools and documentation are MIT-licensed. Bethesda and upstream creators retain their asset rights. Public release assets intentionally contain no NIF/BSA/DDS files; the third-party mesh FOMOD is not approved for redistribution by this repository's MIT license.
