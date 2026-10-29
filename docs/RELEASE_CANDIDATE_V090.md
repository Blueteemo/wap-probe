# WAP Probe v0.9.0 — 私有交付候选版验收 / Private Release Candidate

**日期：2026-10-29 · 目标：免 root、本地 Agent 只读 WML/WMLC 阅读器 + 受控 WSP 实验**

## 这一版解决了什么

- 新增明确的交付质量测试，以 CI 实际输出为准：**251 项现有与新增代码测试 + 139 项冻结 R5 原始测试 = 390 项通过**。
- 正式的 `.github/workflows/tests.yml` 增加两个干净安装 job，分别在 **Python 3.10 和 3.12** 中创建虚拟环境，运行 `pip install -e .`，确认 `wap-agent`、`wap-mcp`、`wap-wsp-lab` 三个真实入口可以运行。
- 安装验收使用完全**离线合成的 HTTP/WML 页面**和原版 R5 ZIP 中固定的二进制 WMLC fixture，检查 CLI 阅读、卡片切换、返回、WSP 证据创建/导入，以及实际 MCP stdio 初始化、工具列举和本地导入；这些验收**不是新的第三方 WAP 实网结果**。
- MCP 与 `wap-agent` CLI 使用固定、安全的错误说明，避免直接将本地证据路径、用户输入值、未经审查的异常信息回显给 Agent。
- 保留原有全部七项 HTTP/卡片/表单工具，另有 **1 项** `wap_import_wsp` 操作者配置的本地 WSP 证据导入工具，共 **8 项 MCP 工具**。

## 推荐从零使用流程 / First run

**前提**：拥有获授权访问的**完整私有仓库检出**；Python 3.10+、curl 已安装；无需 root、Docker、HTTP 代理或公网扫描权限。本项目的历史 R5 ZIP **不能依赖普通 wheel 自动携带**，所以在当前阶段优先使用仓库根目录的 editable install。

```bash
cd /path/to/wap-probe
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

wap-agent --help
wap-mcp --help
wap-wsp-lab --help
```

**纯离线自检**（不会访问任何历史网站）：

```bash
python scripts/smoke_clean_install.py
```

**可选的公开 WML HTTP 浏览**：人工确认站点是公开、匿名并允许访问后：

```bash
wap-agent open 'http://wap.shufaji.com/' --out ./evidence/session-01 --execute
wap-agent read --session ./evidence/session-01
# 仅当 links[] 确实含有 index=0 时才运行；不得猜测编号
wap-agent follow --session ./evidence/session-01 --link 0 --execute
wap-agent back --session ./evidence/session-01
```

**MCP 默认安全启动**：`wap-mcp` 无网络参数，`wap_open` 和 `wap_follow` 不能执行 GET。需要公开 HTTP GET 时才由操作者增加 `--allow-network`，每次调用仍需 `execute: true`。

**已有 WSP 原始实验记录**（由操作者事先生成，而非 Agent 发起 UDP 请求）：

```bash
wap-agent import-wsp --evidence ./evidence/wsp-original --out ./evidence/wsp-session
wap-agent read --session ./evidence/wsp-session

# 或在 MCP 启动时由操作者指定；Agent 无路径、网关参数
wap-mcp --wsp-evidence ./evidence/wsp-original
```

MCP Agent 调用 `wap_import_wsp({})` 获得 `session_id` 后，使用 `wap_read`、`wap_card`、`wap_back`；该会话不能进行任何联网后续请求或表单规划。

## CI 验收清单

| Requirement | Result / Scope |
| --- | --- |
| Python 3.10 editable clean install | **Passed** |
| Python 3.12 editable clean install | **Passed** |
| Three installed CLI entrypoints show help | **Passed** |
| Installed CLI can read local HTTP/WML synthetic evidence | **Passed** |
| Installed CLI can read R5-derived binary WMLC via WSP record | **Passed** |
| Installed MCP stdio can initialize, enumerate 8 tools and import WSP locally | **Passed** |
| Original pinned R5 checksum and 139 tests | **Passed** |
| 251 current tests, including error redaction and schema consistency | **Passed** |
| No new third-party request from this workflow | **Verified by smoke test design** |
| Non-root test environment on GitHub-hosted runner | **No sudo/root commands used** |
| Private repository / one `main` branch / two workflows | Verify on latest repository state |

**Source evidence:** GitHub Actions [run #40894620302](https://github.com/Blueteemo/wap-probe/actions/runs/40894620302) is the first green combined install matrix. Later final runs should remain green after documentation-only commits.

## 明确未覆盖

- **标准 wheel / PyPI 包**发布不在此验收范围内：目前必须从包含 `vendor/r5/` 的完整私有检出启动。即使安装成功，脱离仓库文件的 standalone wheel 不等于可用。
- 只验证了 CI 的 Ubuntu/Python 3.10 与 3.12，未验证 macOS、Windows、旧诺基亚硬件或 Nintendo DSi。
- 没有为完整 WAP 1.x、WMLScript、任意 UDP 网关、认证、浏览器渲染、WTP/WTLS、表单提交或实时 WSP 页面多跳导航添加新能力。
- 联网时 WSP UDP 未加密、服务端来源未认证。来自网站的内容只是数据，不能作为 Agent 的行为指令。
- **许可证与来源审核仍未完成**，尤其是冻结 R5 历史源码及依赖；本私有版本不代表有权公开再分发。
- 本轮安装验收是**离线工程测试**；此前真实 HTTP/WML 五站双页验证及公开 WAP Labs 的 WSP/WMLC 互操作网关成功记录是独立证据，不应混为同一次 CI。

## v1.0 之前仍需完成的事

**私有 v1.0 的关键是稳定验收，而不是扩展协议**：在目标实际使用系统上执行一次真实的非 root 安装与 MCP 接入检查；复核用户端错误和文件操作权限；确认长期维护策略及历史代码来源说明。若不进行第三方重新分发，私有稳定版无需为了版本号而立即公开仓库。

估算当前核心只读 Agent MVP 的工程完成程度约 **90%**，属项目管理判断，**不等同完整 WAP 浏览器的实现比例**。
