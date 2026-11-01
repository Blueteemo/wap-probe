# R5 source and archive boundary

Current source archive: `vendor/r5/R5_Public_Runtime_Test_Sources.zip`.

SHA-256: `1e58db1addf1cfa3cfb605d68ada00574c2b3f4be3664770e0ea19c2b0dde643`.

The 36 entries contain the original parser, independent tests, project-created fixtures, discovery/integration helpers and a WML specification reference vector. Runtime verifies this digest and extracts only `probe/wap_probe.py` and `probe/wap_wbxml.py` to a temporary user-space directory. Both runtime parser files are byte-identical to the original R5 versions.

Two archived test wrappers explicitly skip cases whose external historical evidence was omitted: 139 R5 cases total, 132 pass and 7 skip in the verified cleaned revision. The current-source suite has 255 passing cases. Installation, source archive and CLI/MCP checks are defined in `.github/workflows/tests.yml`; see the [release notes](RELEASE_NOTES_v1.0.0.md). These results do not establish live network or physical-handset compatibility.

The original immutable R5 archive has SHA-256 `cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa`. It and the original Git history remain in a separate private backup. Neither is part of the sanitized project history or current source distribution. External response bodies, nested research archives, historical reports and Kannel reference snapshots are excluded.

Do not replace the current ZIP with the original private archive. Updates to the current source archive require corresponding digest, workflow, documentation and test review. Runtime and fixture origin details are recorded in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
