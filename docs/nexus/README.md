# Nexus preparation

## Prepared fields

- **Title:** Bow Sight Windows VR - Left and Right Handed
- **Version:** 0.3.0
- **Game:** Skyrim Special Edition, with VR targeting stated prominently
- **Summary:** Physical bow sight windows with an arrow shelf and a narrower section above the grip. Choose left- or right-handed meshes through a FOMOD installer. No aiming, damage, ballistics or runtime plugin changes.
- **Description:** [description.bbcode](description.bbcode)
- **Changelog:** [../../CHANGELOG.md](../../CHANGELOG.md)
- **Preview:** [../images/iron-bow-comparison.png](../images/iron-bow-comparison.png)
- **Credits / permissions:** [../ASSET_PERMISSIONS.md](../ASSET_PERMISSIONS.md)
- **Support:** GitHub Issues; request bow name, hand choice, game/modlist version and winning mesh provider.

## Before publishing a bundled mesh mod

- [ ] Identify and clear redistribution terms for all third-party assets in the selected upload.
- [ ] Add required original-author credits and permission evidence; select Nexus permission settings that actually match those grants.
- [ ] Decide whether the public package targets the current MGO sources or a separately prepared stock-vanilla source set. Version 0.3.0 targets MGO sources.
- [ ] Rebuild locally from the supported sources, run verification and test the ZIP through MO2's FOMOD UI.
- [ ] Confirm the right-handed view, unique bows, Bound Bow flame/refraction effects and the revised 0.3.0 proportions in-game. Do not describe these as exhaustively tested yet.
- [ ] Add in-game images showing several bow families; label the existing image as a neutral-shaded geometry render.
- [ ] Declare actual texture/material/unique-model dependencies and conflicts; note that another mesh replacer or regenerated PGPatcher output can overwrite the cutouts.
- [ ] Upload the verified FOMOD as the main file only after the permission and compatibility work above is complete.

No Nexus page has been created or uploaded by this project. The draft is intentionally separate from the public source release. A source-toolkit upload, if desired, should be described as a tool/modder resource and must not imply that it contains install-ready meshes.

## Local mesh package behavior

The FOMOD installs exactly one of two complete 34-path mesh sets. It never installs both handedness choices together and contains no ESP/ESL or DLL. Reinstall/replace to switch hands. Disable the mod to restore the previous winning mesh providers.
