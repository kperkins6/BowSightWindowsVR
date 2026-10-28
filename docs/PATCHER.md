# Standalone Bow Sight Patcher

The patcher reads the bows in your own Skyrim SE/VR mod list and generates a separate mesh-only mod. It has no MGO dependency and ships no game assets. Python 3.11 or newer and a browser with WebGL are required; no Python packages or internet connection are needed.

## Start

On Windows, double-click **Start Patcher.cmd**. Alternatively run `python patcher.py`. Keep the launcher running while editing. It opens a local page in your default browser; closing the launcher stops that page's backend.

## Recommended: build everything with defaults

The main workflow is at the top of the page. Individual review is optional.

1. **Find your bows:** choose your mod list and click **Find bows**.
2. **Build with defaults:** choose your shooting hand and click **Build all supported with defaults**. This replaces custom opening settings, builds and validates every supported mesh, and presents counts for successes, failed defaults and unsupported files. Nothing is approved or written to an output mod yet.
3. **Approve & generate:** choose a new output folder, then click **Approve N successful & generate mod**. All successful results are approved together and exported. Failed and unsupported meshes are automatically excluded, so they do not block the rest.

Open the summary's failure/warning lists if desired. **Inspect** opens the optional **Inspect or adjust individual bows** section, which contains the existing 3D editor and manual batch tools. If you manually change the successful selection or include a failed mesh, the quick summary becomes stale; rebuild defaults or finish through individual review. Changing hands requires a new default build.

The automatic run is held in the current session. Saving a project preserves per-bow settings and approvals; after reopening an unapproved run, click **Build all supported with defaults** again to recreate its live validation summary.

## Choose the input mod list

To preselect a profile:

```powershell
python patcher.py --mo2 "D:/Modding/MO2/ModOrganizer.ini" --profile "My Profile"
```

1. Select **Mod Organizer 2 profile**, browse to ModOrganizer.ini, and click **Detect**. Choose a profile. Paths to the game, mods, profiles and overwrite directory come from that installation's configuration.
2. For Vortex/manual installations, choose **Deployed Data** and supply the game Data folder and active plugins.txt. An optional loadorder.txt supplies explicit plugin ordering. For an MO2 installation using unusual virtual-file rules, this mode can also run against Data from inside MO2's virtual filesystem.
3. Supply the effective game INI when archive loading is customized. In MO2 mode the tool looks for profile INIs, then the game's document-folder INI; without one it reports its standard-archive fallback. Do not proceed on assumptions if your setup uses a different archive configuration.
4. Click **Find bows**. Discovery follows winning WEAP records, their model paths, weapon-template fallbacks, first-person STAT references and matching display/first-person variants. Multiple weapons sharing a mesh appear together. Crossbow animation types are excluded; creature/dummy records classified by the game as bows can still appear.

The scanner uses active plugins rather than looking for “bow” in every filename. Loose meshes win over BSAs. MO2 mod priority and overwrite are respected; BSA filenames are resolved through that priority, then loaded in INI/plugin order. Disabled mods are excluded. If a manager uses additional archive-redirection rules, use its deployed/virtual Data view or provide its actual INI. This is not a replacement for the game engine's entire virtual filesystem.

## Optional: preview and adjust

- Choose **Left-handed** for bow in right hand/string in left, or **Right-handed** for the reverse.
- Select a mesh. Original and generated geometry use a synchronized camera. Drag to rotate, wheel to zoom, shift-drag to pan. Sight view, side view and three-quarter views make it easier to inspect protrusions. **Focus opening** frames the cutout; **Fit bow** restores the full view.
- Adjust shelf position, opening height, upper taper, shelf bevel, depth and inner boundary. Values are in model units. Automatic depth follows the reference algorithm; manual depth is a fraction below 0.99. Raising depth makes a deeper opening. The inner boundary controls where lateral narrowing stops.
- Select individual shapes to edit. For example, retain an unrelated effect layer or decoration. Static embedded parts remain visible and unchanged. Review every warning about unsupported or retained geometry.
- **Protect bowstring** preserves the standard string islands. For unconventional strings, inspect all views carefully; this protection recognizes the reference Skyrim geometry layout rather than every conceivable custom string.
- **Approve & next** records the exact preview and advances to the next unreviewed mesh. **Skip bow** omits it. Any geometry setting or hand change invalidates the affected approval.

The viewer shows the actual quantized output vertices and triangles, in a neutral material. It does not reproduce textures, game shaders, magical animation, a drawn animation pose, eye position or headset occlusion. Defaults match the finished reference sight window but are not an automatic measurement of a custom bow's arrow rest. Check unusual designs in game after installation.

## Batch mode

Enable **Batch selection** above the bow list. Check individual meshes, or use **Select all filtered** after searching/filtering. Selection persists across filters; the counter includes hidden selections.

- **Apply current opening** copies the current mesh's opening parameters to the selected supported meshes. Shape IDs remain individual, since they differ between NIFs.
- **Preview selected** generates each selected supported mesh and creates before/after cards focused on its opening. Click a card to inspect that bow in 3D. Unsupported selections are left unchanged.
- **Approve previewed** approves the selected supported meshes only when all have successful, current previews. Changes to hand/settings require previews again. Batch approval is your decision after inspecting the cards and any unusual bows.
- **Include selected** and **Skip selected** control which meshes will be generated. Skipping clears approval.
- **Skip unreviewed** near the output controls is useful when generating a subset: reviewed meshes remain included and other meshes are omitted.

## Save and generate

**Save project** downloads a local JSON containing source paths, hashes, per-bow parameters, inclusion and review state. **Open project** rescans its mod list and only restores approvals for matching sources. Projects contain installation paths: keep them local.

Choose a **new output folder outside all source folders**, then click **Generate mod + ZIP**. Every included supported mesh must be approved. Unsupported meshes are listed but omitted. Generation rechecks active-plugin/profile snapshots, refreshes asset priorities and validates each source hash, then reproduces the reviewed bytes. It stages all meshes and validates the ZIP before publishing the new folder and archive. Existing outputs are never overwritten.

Profile validation compares file contents and MO2 resource paths. Rewriting identical profile files or changing MO2 window/UI settings does not invalidate your reviews. Changing the active mod/plugin lists, archive INI contents, resource paths or source meshes requires a fresh scan.

Install the resulting ZIP through your mod manager and let it win conflicts with its source bow meshes and later mesh-generating tools. Disable the earlier sight-window mod before enabling this output. The patcher does not install/enable the output or change your load order. A manifest marks generated mods so later MO2 scans can exclude them. In deployed mode, disable/remove previously deployed sight-window output before rescanning; it cannot reconstruct originals from overwritten files.

## Supported layouts and limitations

Discovery supports Skyrim SE/VR ESP/ESM/ESL records and BSA versions 104/105, including zlib/LZ4 assets. Editing currently supports SSE NIF 20.2.0.7, user 12, Bethesda stream 100, a single skin partition per shape, 40/44-byte packed vertices and identity bone palettes. It requires Bow_MidBone and a measurable Y-oriented bow frame. Older NIF streams, unskinned-only bows, multiple partitions and other bone palettes are reported as unsupported rather than modified. Convert those externally with an appropriate NIF tool before rescanning.

Original materials, texture references, skeleton/collision blocks and original skin weights remain intact. New edge vertices interpolate attributes; supported Bound Bow effect layers can require reduction to four bone influences, reported in the preview. The source mods and their textures/materials remain prerequisites for your locally generated output. The patcher itself has no dependency on any particular mod list.

## Development verification

```powershell
python -m unittest discover -s tests -v
python -m compileall -q tools patcher.py
python tools/audit_public.py
```

Tests generate synthetic plugins, BSAs and NIFs instead of including game assets. They cover override/deletion/type changes, templates/first-person references, both archive compression formats, asset priorities, custom window profiles, batch review, stale input detection, output isolation, preview/export topology and local API authorization/concurrency.
