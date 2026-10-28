# Bow Sight Patcher 1.1.1 preview

Batch building is now the recommended workflow at the top of the page:

1. **Find bows** in your mod list.
2. Choose your hand and **Build all supported with defaults**.
3. Choose an output folder and **Approve successful & generate mod**.

All supported meshes are built and validated automatically. A summary lists successes, failed defaults and unsupported files. One approval exports all successful results; failures are excluded and do not block the rest. Individual visual review is optional, and the 3D editor/manual batch tools are in a collapsed section below.

Download **BowSightWindowsVR-1.1.1-preview-SourceToolkit.zip**, extract it and run **Start Patcher.cmd** or `python patcher.py`. Requires Python 3.11+ and a WebGL-capable browser. No extra Python packages or internet connection are needed.

This source-only download contains no game meshes. Editing retains the same supported SSE NIF layouts and limitations as the previous preview. Generated output stays local and separate from your installed mods.
