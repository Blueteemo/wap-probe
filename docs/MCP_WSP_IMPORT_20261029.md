# v0.8.3｜MCP 安全导入本地 WSP 会话 / Operator-Configured Offline WSP Import

**2026-10-29 · Private Agent integration, no new public network access**

## 功能 / Capability

The MCP server now offers a **single host-configured local WSP evidence importer** named `wap_import_wsp`. Unlike the experimental `wap-wsp-lab` CLI, it **cannot send UDP** or select a website. The Agent tool takes **no arguments at all**, specifically no file path, URL, gateway, network permission or execution flag. A local operator chooses the WSP record at MCP startup:

```bash
# Optional: create one original anonymous public lab record explicitly.
wap-wsp-lab --lab --allow-network --execute --evidence-out ./evidence/wsp-original

# Start the MCP server with an operator-selected *existing* evidence directory.
wap-mcp --wsp-evidence ./evidence/wsp-original
```

The Agent then calls `wap_import_wsp` with `{}`. The returned opaque `session_id` works with the **existing** `wap_read`, `wap_card` and `wap_back` MCP tools, exactly as in the Agent CLI. No raw local path, original binary PDU, response headers, or credentials are returned.

Calling `wap_import_wsp` again returns the **same** session after revalidation, rather than cloning unbounded copies. The imported session exists only within the MCP process's ephemeral local directory; restarting the MCP server requires reimporting from the operator-selected original WSP record.

## Offline-only boundary / 安全边界

- WSP evidence is read from the **server operator's startup flag**, never from `tools/call` arguments. Without this startup flag, the import tool fails.
- The existing `wsp_evidence.verify_record` validates exact allowlisted lab GET bytes, Reply transaction ID, status, MIME, original PDU SHA-256 and file sizes; frozen R5 independently parses the resulting WML/WMLC cards.
- Every subsequent read rechecks the packet, body and R5 export against the original binary, to detect local tampering.
- Imported `wsp-offline` sessions have no followable `links[]` or `do_links[]`, and `wap_follow`, `wap_go` and `wap_form_plan` reject these sessions even when the **HTTP MCP server** has `--allow-network` enabled.
- The WSP lab CLI remains the only UDP client and retains its fixed public first-party test endpoint and two explicit network opt-ins. Importing a record **never** triggers this CLI.
- This is an **integrity check, not authenticated source provenance**. `source_authenticated: false` remains visible. Hashes do not establish the identity of an unencrypted UDP gateway.

## Tests / 验证

`tests/test_mcp_wsp_import.py` adds **8 offline MCP regression cases**: normal import and two-card navigation, repeat import, startup configuration, refusal of arbitrary path/gateway arguments, HTTP network permission isolation, local packet tampering, operator source changes after import, and startup flag propagation. Tests verify no socket/curl activity for import/read/card/back.

The normal offline GitHub Actions suite continues to exercise 139 original frozen R5 tests; no one-shot network workflow was created in this round.

## Out of scope / 未实现

No general WSP/WDP browsing through MCP, arbitrary UDP gateways, WTP/WTLS, WMLScript, authentication, cookies, form submission, or original-vintage-device compatibility. Imported evidence is a **one-page transport capture** that may contain multiple WML cards; it cannot fetch second-page links.

See [WSP evidence format](WSP_OFFLINE_EVIDENCE_20261029.md) and [WSP first-party live lab verification](WSP_READONLY_LAB_20261029.md) for source and transport limitations.
