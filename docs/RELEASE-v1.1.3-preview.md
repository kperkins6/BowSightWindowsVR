# Bow Sight Patcher 1.1.3 preview

The current-bow editor and batch actions now have explicit scopes. Editing opening controls changes only the current bow. A separate **Copy this bow’s opening to N selected bows** action copies it to checked targets.

The batch workflow is grouped into four steps: choose targets, optionally copy an opening, preview/approve targets, and generate the output mod. Controls show the source bow, target count, current-preview count and project-wide output readiness. Select-all adds supported filtered bows; preview cards show selected targets only. Approve/exclude labels are consistent across individual and batch controls. Output generation uses all included, approved bows in the project, followed by ZIP installation through the user's mod manager.

Both 3D panels also show an optional cyan arrow-position reference. It is an estimate based on the bow rig and earlier Long/Glass Bow telemetry, mirrored for handedness; it stays fixed when editing the opening. It is not an exact contact measurement for every custom bow.

Requires Python 3.11+ and a WebGL browser. Extract the source package and run **Start Patcher.cmd**. The MGO one-click workflow remains available at the top.

Validation: 48 automated tests; browser checks of single-bow edit isolation, explicit batch copy, preview/approval, selection versus output inclusion, exclusion and shared output controls. Public assets contain source/tools only; generated game meshes remain local.

Known issue from 1.1.2 preview: a repeat Windows export in a cloud-synchronized directory was denied during the final staging-directory move. The cause remains unresolved; this UI update does not change that export implementation. Investigate filesystem permissions, synchronization activity and any security alert before retrying a denied export.
