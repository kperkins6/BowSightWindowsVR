# Standalone Patcher Implementation Plan

> **For agentic workers:** Use executing-plans to implement these tasks in this session. Steps use checkbox syntax for tracking.

**Goal:** Discover, preview, adjust and generate bow sight meshes from an arbitrary supported Skyrim SE/VR mod list.

**Architecture:** Read-only plugin and asset discovery feeds a local project and bounded mesh operation. A loopback browser UI uses the same generated geometry as output. Output is staged, validated, and separate from inputs.

**Tech Stack:** Python 3.11+ standard library, HTML/CSS/JavaScript/WebGL; existing NIF tools.

**Spec:** ../specs/2026-10-28-standalone-patcher-design.md

## Global Constraints

- No MGO paths or redistributed meshes in public files.
- No writes to source mods, game data, load order or runtime settings.
- Explicitly block unsupported NIF variants; preserve opaque blocks.
- Only reviewed meshes are generated; changes invalidate review.
- Bind HTTP to loopback with per-run request token and origin checks.

## Review Focus

- Plugin overrides change a bow into another weapon type or delete it: omit it.
- Loose assets override archives regardless of plugin order; MO2 overwrite wins.
- Stale project or changed source: reject generation rather than patch different bytes.
- Nested or existing output path and path traversal: refuse before writing.
- Unusual shapes or malformed records: report per-item failure without silently dropping data.

### Task 1: Discovery

Files: tools/patcher_records.py, tools/patcher_assets.py, tools/patcher_scan.py; tests/test_patcher.py.

Interfaces: scan(config, progress=None) -> dict with config, bows, warnings; AssetIndex.read(path) -> bytes and source description. Config accepts mode, mo2, profile, data, plugins, output exclusions.

- [x] Add failing synthetic plugin override, template/STAT, BSA compression and asset priority tests.
- [x] Implement bounded plugin reader and form identity mapping, BSA104/105 indexing/decompression, MO2/deployed resolution and scan provenance.
- [x] Run tests and real-profile scan; save private report in build/.

### Task 2: Parametric geometry and project/output

Files: tools/window.py, tools/patcher_project.py; tests/test_patcher.py.

Interfaces: apply_window retains existing defaults, accepts optional profile; Project.preview(id, settings), approve(id), generate(output), save/load local JSON. Snapshot sources and settings bind approval.

- [x] Add failing adjustable-cut, approval invalidation, source-change and protected-output tests.
- [x] Implement profiles and validation, actual before/after geometry, shape selection, review state, save/load and staged ZIP output.
- [x] Check released reference meshes remain byte-identical with default settings; verify both hands on real inventory.

### Task 3: Desktop browser application

Files: patcher.py, tools/patcher_server.py, app/index.html, app/app.js, app/viewer.js, app/style.css, docs/PATCHER.md.

Interfaces: JSON endpoints for defaults, scan/progress, model preview, settings, approval, save/load and generate; requests require per-session token. Browser never sends arbitrary asset paths to file endpoints.

- [x] Add API access-control and project workflow tests before implementation.
- [x] Build asynchronous scan status, filterable list, synchronized before/after WebGL viewer, settings and shape controls, skip/review and export with clear errors.
- [x] Add user-requested batch selection, filtered select-all, presets, preview cards and approval/include/skip actions.
- [x] Browser QA actual mod list, saving and generated output; test project restoration in the automated suite; document launcher and limitations.
- [x] Whole-branch independent review, fix important findings and run suite/audit.
