# WAP Probe 整体开发路线与验收范围 / Project Roadmap

**2026-10-29 · Current status: v0.9.0 (private RC) · Private repository**

## 进度口径

按现阶段明确的**免 root、Agent 使用、WML/WMLC 只读阅读 + 有边界 WSP/WDP 实验**这一 MVP 衡量，目前属于**约 90% 的工程进度估算**。这不是代码覆盖率或自动生成的精确百分比，而是根据功能完成度、测试、真实来源验证和交付准备做的主观判断。目标若变成“完整 WAP 1.x 手机浏览器”，此百分比即不适用。

| Area | Status (v0.9.0) | Evidence |
| --- | --- | --- |
| Historical WAP investigation & immutable R5 | Complete for frozen research scope | R5 archive SHA-256 + 139 original tests; historical reports |
| HTTP(S) public WML Agent reader & safe same-origin navigation | Core usable | Five known WML origins, two-page reads; CLI & MCP |
| WMLC/WBXML decoding with independent references | Narrow compatibility verified | 23 pinned Lowband cases, controlled HTTP binary fixture |
| WML form preview & GET dry-run plan | Read-only only | Fail-closed form and URL tests; no submit |
| WSP/WDP connectionless GET lab | Experimental, deliberately allowlisted | One real WAP Labs WSP 200 WMLC response; local UDP tests |
| WSP packet evidence & offline card import | Usable locally | Exact-packet hashes, frozen R5 reparse, Agent CLI and MCP |
| Agent/MCP usability and artifact packaging | Private release candidate | Clean Python 3.10/3.12 editable installs, installed CLI/MCP offline smoke; full private checkout still needed |
| General old-phone WAP protocol conformance | **Out of MVP scope** | WTP, WTLS, scripts, sessions, carrier networks and GUI not implemented |

## Next milestones / 剩余里程碑

**v0.9.0 — private release candidate / 当前已完成**

1. **Passed:** clean editable installation on Python **3.10 and 3.12**, plus installed `wap-agent`, `wap-mcp`, `wap-wsp-lab` entrypoints and offline HTTP/WML + WSP/WMLC end-to-end smoke.
2. **Passed:** version/tool metadata consistency tests and fixed user-facing CLI/MCP error messages that do not leak local paths or input values.
3. **Documented:** single [release candidate first-run guide](RELEASE_CANDIDATE_V090.md) distinguishes synthetic offline tests from historic live HTTP and public WSP interop evidence.
4. **Preserved:** no scheduled third-party WAP requests, one `main` branch, two existing workflows, frozen R5 checksum and original test suite.

**Before private v1.0 / 私有稳定版剩余**

1. Run one first-run install and MCP session check on the **actual intended user's system** (not only hosted Ubuntu runners); note macOS/Windows platform limits honestly.
2. Inspect operational and maintenance details (filesystem permissions, cancellation/timeout behavior, troubleshooting, R5 provenance and dependency rights).
3. Decide whether private v1.0 should remain source-checkout only or fund a supported distributable package; do **not** announce a standalone wheel/public release without tests and license permission.

**v1.0 (private stable) — defined completion criterion**

- A clean user checkout can open a verified public WML page via HTTP and navigate one safe same-origin link.
- Frozen R5 decodes WMLC test fixtures; Agent reads multi-card WML/WMLC with correct bounds.
- The operator can capture one allowlisted anonymous WSP lab response, save a source-bound record and import it offline into CLI/MCP for read/card/back.
- No POST, cookie/login, script execution or arbitrary UDP endpoint can be triggered through the MCP tool set.
- Current and frozen regression suites pass, with documented test provenance and security limitations.

**Explicitly deferred / 刻意不纳入 MVP**: graphical rendering, S60/DSi/Nokia hardware ports, WSP general gateways, WDP segmentation, WTP, WTLS, dynamic script execution, write-capable forms, authenticated services and broad unknown-site crawling. This repository is **not WAPDS**; scope and evidence are separate.

## License and distribution

The repository stays private while provenance and redistribution rights for historical bundled frozen R5 artifacts/dependencies remain unreviewed. Passing tests does not establish legal permission to publish the full source/archive, so a public GitHub release is **not** an automatic v1.0 step.

## Progress methodology

This estimate rewards completed, tested **MVP user workflows**, not count of commits, lines of code, or version number. Expanding into general WAP browser features changes the denominator and needs a separate project plan. During maintenance, prefer consolidating tests/docs over creating tiny patch releases and temporary Actions workflows.
