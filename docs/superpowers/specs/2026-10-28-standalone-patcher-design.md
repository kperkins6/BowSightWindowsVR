# Standalone Bow Sight Patcher

The user approved a standalone patcher which discovers bows from their mod list, offers left/right handed output, and previews and adjusts unusual models before creating a separate output mod. The finished 1.0 mesh package remains available independently.

## Product

A Python 3.11+ launcher opens a local browser interface, served on loopback only. No third-party runtime packages, downloaded scripts, telemetry, or redistributed game meshes. The interface has setup, a searchable bow list, an interactive neutral-shaded original/patched viewer, and output generation. Browser drag rotates both views, wheel zooms, and fixed side/front views expose the opening. Hand descriptions identify bow hand and string hand explicitly. Left-handed is the initial choice for this user; the application supports both equally.

MO2 mode accepts the installation's ModOrganizer.ini and profile, reads configured game/mod/overwrite paths and active plugins, resolves winning loose files and loaded BSAs. Deployed Data mode accepts Data and a plugins/loadorder file for Vortex, manual installations, or launching through a virtual filesystem. All discovery is read-only. No hardcoded MGO paths in distributed code. Existing patch output is excluded to avoid double editing. Ambiguous archives, missing plugins or records, and unsupported geometry are surfaced, never silently represented as supported.

Bow discovery follows final WEAP overrides (DNAM type 7), template inheritance, referenced first-person STAT models, and matching display/first-person variants. All plugin origins are included, including mod-added and bound bows. Deleted records and crossbows are excluded. Canonical vanilla paths can be discovered through their records without a source hash restriction. Duplicate mesh paths share one adjustment entry while listing all associated weapons. Records retain origin and winning plugin provenance.

## Editing

The user additionally requested batch selection. Include per-row checkboxes, select-all matching the current filter, clearing selection, transferring the current opening settings while preserving individual shape choices, generating before/after opening cards, and approving/including/skipping the selection. Batch approvals require current successful previews. A fresh scan or project load clears selection and preview cards. Unsupported selections remain explicit and are ignored only by edit/approval actions.

Reuse the bounded SSE stream-100 skinned NIF reader/writer. Unsupported streams, partitions, palettes, or missing bow rig are blocked with a specific explanation; they do not prevent reviewing supported bows. Preserve unknown blocks, materials, texture paths, skeletons, original skin weights, strings, and original files. The preview uses the actual generated geometry, not an artistic approximation. Include unedited static geometry when supported or explicitly warn if not visible.

Controls: handedness, shelf position, opening height, taper height, bevel, depth, lateral inner boundary, string protection, and per-shape enable/disable. Defaults reproduce the released geometry for the known reference meshes. Adjustable coordinates are rig/model units; the shelf is a guide, not an inferred eye position. Nonstandard mesh orientation is blocked pending external rig conversion rather than guessed. Provide reset, skip, review/approve, and save/load project JSON. Geometry-affecting edits invalidate approval. Generated output includes only approved, included models. Hand changes invalidate every approval.

## Output and safety

Write to a new, separate folder and optional installer ZIP, never overwrite originals or auto-enable in a live mod manager. Validate source hash at generation against scan snapshot, all input/output paths, finite vertices, triangle indices/areas, weights, and opaque block preservation. Stage all outputs before exposing a complete result; failures produce no finished mod. Include a manifest with source hashes, providers, parameters and results for reproducibility. A marker allows future scans to exclude generated output. The UI reports included/skipped/unsupported counts. Saved projects are local and must not be packaged publicly.

## Builder decisions

Implement in the existing independent repository on a feature branch. Standard-library HTTP backend, dependency-free WebGL viewer, native folder/file picker via tkinter when available with text paths as fallback. Read-only real-profile scan and isolated output verification are authorized; installing/enabling or publishing this new application is a separate action. Test synthetic plugins/BSA, override and asset priority, malformed inputs, hand/settings approval invalidation, safe output, and actual local meshes. Use browser QA for setup, selection, preview adjustment, approvals and generation. Local real-world reports live in ignored build/.
