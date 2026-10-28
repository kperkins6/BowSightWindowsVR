# Implementation evidence

User authorized the standalone scanner, handedness selection, adjustable previews and output mod, then explicitly added batch selection. Implemented in the existing independent repo on codex/standalone-patcher. The released reference builder remains unchanged in behavior.

- Discovery: synthetic override/deletion/type, template/STAT, BSA104/105, compression toggle/embedded names, loose priority, MO2 reversed mod ordering and existing output exclusion tests passed.
- Geometry/project: custom profiles, rig/layout blocking, preview-bound approval, save/load source revalidation, nested/existing output guards, stale source/asset priority/profile checks, opaque block preservation and batch review tests passed.
- Local API: token/origin/host checks and deterministic concurrent-export mutation regression passed.
- Actual local profile: 2,012 active plugins; 635 bow records; 75 unique paths; 68 supported editable layouts; seven dummy/legacy/unskinned layouts explicitly blocked. Final bounds validation found one custom mesh needs a right-hand opening adjustment. These are local verification results, not universal compatibility claims.
- All 34 reference output hashes match in both hands with default settings.
- Isolated export generated 68 left-handed and 68 right-handed meshes plus validated ZIPs; every scanned original source hash remained unchanged. No installation, load-order change or public upload was performed.
- Independent code review findings fixed: serialized preview topology, concurrent mutation during export, archive-name false filtering. Additional fixes cover unresolved references, refreshed asset priorities, output.zip collisions/rollback and stale profile snapshots.
- Independent batch review finding fixed: clear selections/cards when a new scan/load replaces the project. Browser checks also identified and fixed selection checkboxes remaining disabled after batch actions and prevented setting edits during batch preview.
- Final automated suite: 34 tests passed. Manual bounds regression rejects extreme opening settings that would exceed original shape bounds.
- Browser workflow verified: hand switching invalidates review, live numeric adjustments persist, two filtered bows receive a batch preset, both before/after cards render, batch approval succeeds, and output contains exactly the two approved left-handed meshes with the selected height. A fresh scan resets selection/cards/approvals and restores defaults. Project download was verified locally.

Ruling: use the approved workflow as the implementation scope; settle platform details in the existing Python codebase without another permission round. The local browser app requires Python 3.11+ and WebGL; no third-party packages. Unsupported NIF layouts stay listed and blocked rather than being converted implicitly. Actual neutral-shaded geometry is previewed, not game shaders or a drawn animation. These limits are documented in PATCHER.md.

Terminal note: local HTTP test connections were blocked by the execution sandbox (WinError 10013). The same tests passed with explicitly approved loopback access. A CIM process inventory was unavailable; no antivirus warning was supplied, that inventory action was not retried, and no protection settings were changed. Long discovery scans were cancelled through their own execution sessions after a file-lookup performance issue was identified; loose mesh indexing corrected it.
