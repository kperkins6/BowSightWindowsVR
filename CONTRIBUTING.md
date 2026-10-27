# Contributing

Run `python -m unittest discover -s tests -v` and `python tools/audit_public.py` before submitting changes. The latter checks tracked files; stage only intended source/documentation changes first.

Keep game and mod assets local. Do not commit NIF, BSA, DDS, mod-manager profiles, telemetry captures, credentials or machine-specific manifests. Do not attach a locally generated mesh ZIP to public issues or pull requests without establishing the applicable redistribution permissions.

For another source family, supply source URLs, permissions, format/transform details and hash-based verification. The current reader/writer intentionally supports a narrow SSE layout and identity bone palettes. Do not silently relax those guards.

Preserve the arrow shelf, original vertices' UV/weight data, source skeletons, animation references, collision and materials. Explain any exception. Include geometry previews and state which changes have actual headset testing.
