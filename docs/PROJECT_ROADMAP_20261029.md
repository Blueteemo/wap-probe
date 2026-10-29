# WAP Probe 整体开发路线与验收范围 / Project Roadmap

**2026-10-30 review · Current status: v0.9.0 (private RC) · Private repository**

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

1. **macOS hosted CI has now passed** (macOS 15 / Python 3.12, offline installed CLI/MCP smoke). Still run a first-run install and MCP session check on the **actual user's Apple Silicon Mac**; do not equate hosted macOS CI with local-device validation.
2. Inspect operational and maintenance details (filesystem permissions, cancellation/timeout behavior, troubleshooting, R5 provenance and dependency rights).
3. Decide whether private v1.0 should remain source-checkout only or fund a supported distributable package; do **not** announce a standalone wheel/public release without tests and license permission.

**v1.0 (private stable) — defined completion criterion**

- A clean user checkout can open a verified public WML page via HTTP and navigate one safe same-origin link.
- Frozen R5 decodes WMLC test fixtures; Agent reads multi-card WML/WMLC with correct bounds.
- The operator can capture one allowlisted anonymous WSP lab response, save a source-bound record and import it offline into CLI/MCP for read/card/back.
- No POST, cookie/login, script execution or arbitrary UDP endpoint can be triggered through the MCP tool set.
- Current and frozen regression suites pass, with documented test provenance and security limitations.

**Explicitly deferred / 刻意不纳入 MVP**: graphical rendering, S60/DSi/Nokia hardware ports, WSP general gateways, WDP segmentation, WTP, WTLS, dynamic script execution, write-capable forms, authenticated services and broad unknown-site crawling. This repository is **not WAPDS**; scope and evidence are separate.

## Open source publication / 公开发布

长期私有并非项目要求。目前根目录无 LICENSE、冻结 R5 包有 24 个主要源码文件、10 个嵌套历史源码文件及 10 个误计的 macOS 元数据文件，仍缺少可识别的内部许可证。增强审查已检查 436 个历史 Blob 和一个历史 ZIP，常见凭据特征未发现命中，但不能替代来源、授权与日志审查。详见 [公开发布审查](PUBLICATION_READINESS_20261029.md)。发布建议优先核验 R5 来源后公开完整仓库；若存在不具再分发权限的部分，则使用独立干净历史的可运行公开版本，不直接把现有所有历史暴露出去。

## License and distribution

The repository stays private while provenance and redistribution rights for historical bundled frozen R5 artifacts/dependencies remain unreviewed. Passing tests does not establish legal permission to publish the full source/archive, so a public GitHub release is **not** an automatic v1.0 step.

## Progress methodology

This estimate rewards completed, tested **MVP user workflows**, not count of commits, lines of code, or version number. Expanding into general WAP browser features changes the denominator and needs a separate project plan. During maintenance, prefer consolidating tests/docs over creating tiny patch releases and temporary Actions workflows.
 
## 2026-10-30 v1.0 收尾更新

- **运行时安全收敛完成**：R5 完整 ZIP 仍通过 SHA-256 验证，但 Agent 只展开两份必需解析模块；历史捕获和嵌套资料不再在临时运行目录解包。新增一个离线回归测试。
- **当前回归目标**：252 项主项目测试 + 139 项冻结 R5 测试，共 **391 项**；保持 Python 3.10/3.12 和 macOS 15 的干净安装 CI。
- **公开审查进展**：按文件区分 24 个 R5 主文件、10 个内层历史源码、10 个 AppleDouble 元数据误计；确认 ChatGPT v0.3/v0.3.2 项目基线与本地 DeepSeek 派生审查的开发脉络。已重点阅读 24 个历史 Actions 日志，尚不能替代全部历史公开审查。详见 [审查报告](PUBLICATION_READINESS_20261029.md)。
- **发布决策**：先完成权属确认、外部站点取证材料可分发性核查和所有者许可证选择，再提交同仓库公开方案；单独 wheel、PyPI 和任意 UDP/WMLScript 仍不纳入 v1.0 MVP。
 
### Source-only release preflight

The existing offline test workflow now includes a Git-source-archive install check, using an extracted `git archive HEAD` instead of the checked-out working tree. Its result will determine whether a future **source-only** private/public release can be installed without hidden development state. A wheel or PyPI release remains unsupported until the frozen parser and license/distribution contract are addressed. No tag or GitHub Release is created by this job.
