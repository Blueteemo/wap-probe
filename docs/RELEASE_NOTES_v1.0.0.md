# WAP Probe v1.0.0

WAP Probe provides rootless, local, read-only WML/WMLC tools for Agents: a JSON CLI, an eight-tool MCP stdio server, offline card selection, explicit verified same-origin GET navigation, read-only form previews, and offline GET planning.

- Install from the full Git checkout or Git source archive, including `vendor/r5/`, with Python 3.10+ and curl. A wheel alone is not a complete distribution.
- The separate WSP/WDP lab is opt-in and constrained to explicitly allowed endpoints. Offline WSP evidence import makes no network requests.
- The source-only R5 archive preserves the original runtime parsers and independent regression tests. Historical third-party response bodies and full research archives are privately preserved and excluded from current reachable branch history.
- Owner-controlled sources use MIT, copyright 2026 Blueteemo (千岚之夏). Preserve the Lowband and kXML notices and the exclusions in `THIRD_PARTY_NOTICES.md`. MIT does not cover third-party website bodies or standards.
- No HTML renderer, WMLScript, variable evaluation, form submission, credentials/cookies, general carrier gateway, WTP/WTLS, or physical-handset compatibility is claimed.

The cleaned source passed 387 offline tests with 7 explicit skips for omitted private historical evidence. Linux Python 3.10/3.12, macOS Python 3.12, Git source archive installation and CLI/MCP smoke checks passed. Seven skipped cases require deliberately omitted private website evidence and are not counted as passes.
