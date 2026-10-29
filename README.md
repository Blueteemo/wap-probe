# WAP Probe

**无需 root 的 Agent 专用 WML/WMLC 阅读工具，兼顾传统 WAP 实网取证与研究。**

**简体中文** | [English](README.en.md)

WAP Probe 能让本地 AI Agent 打开公开 WML 页面、阅读正文、选择页面中真实存在的链接继续浏览，并离线返回历史页面。它提供 **JSON 命令行**和**本地 MCP stdio 服务**，无需 root、浏览器自动化、Docker 或常驻网络服务器。

原有冻结 R5 解析引擎、2026 年国内传统 WAP 站点调查和验证证据仍保留在同一仓库。

> **当前仍为私有开发仓库，尚未获准公开再分发。** 随附 R5 历史源码及依赖的许可证／来源尚待审核；请勿因能看到代码就认为已正式开源。

## 功能与支持范围

| 功能 | 当前状态 |
| --- | --- |
| 公开 HTTP/HTTPS GET、公网 DNS/IP 验证、禁用自动重定向 | 已支持 |
| WML 文本（UTF-8、GB2312/GBK、Big5） | 已支持 |
| WML/WMLC 表单结构预览（仅只读） | 输入框、选择项、GET/POST 动作、postfield、变量标记 |
| GET 表单离线请求计划 | 已支持保守字段校验和脱敏预览，不执行 GET/POST |
| 由冻结 R5 解码 WMLC/WBXML 卡片中文正文 | 已支持已覆盖的 WML code page 0 样本 |
| WMLC 优先 HTTP 请求画像 | 可选 `wmlc`；五站仅返回文本 WML |
| 从真实页面提取安全同源 GET 链接 | 已支持，每步仅一项请求 |
| 多卡片 WML/WMLC 阅读、页内 `#card` 索引及离线切换 | 已支持；当前卡片独立显示 |
| 传统 `<do><go>` 无输入导航 | 已支持，独立 `do_links`，每次显式允许联网 |
| 离线阅读/返回、最多 8 份网页、64 条历史动作 | 已支持 |
| JSON CLI、本地 MCP stdio Agent 工具 | 已支持 |
| WMLScript、表单 POST、Cookies/登录、HTML 页面渲染 | 暂不支持 |
| 原生 WSP/WDP 运营商网关、诺基亚实体机兼容 | 未实现／未验证 |

对于二进制 WMLC，当前只能读取 R5 已覆盖的标签、卡片和文本，包含变量或复杂标签的页面可能无法完整还原。**可读正文不等于浏览器视觉渲染、完整标准符合性，更不等于老手机实机验收通过。**

## 环境与安装

- Python 3.10+、PATH 中有 `curl`
- 需要联网时具备公开 DNS/互联网访问能力
- 普通用户权限即可，**不要求 sudo/root**
- 需要包含 `vendor/r5/` 的**完整源码检出**；单独安装不含该归档的 wheel 无法运行 R5 解析器

在仓库根目录执行：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
wap-agent --help
wap-mcp --help
```

也可以不安装，直接使用 `PYTHONPATH=src python3 -m wap_probe.agent_browser` 和 `PYTHONPATH=src python3 -m wap_probe.agent_mcp`。

## Agent JSON 命令行

```bash
wap-agent open 'http://wap.shufaji.com/' --out ./evidence/session-01 --execute
wap-agent read --session ./evidence/session-01
# 仅当 cards[] 中存在 index=1 时，离线切换到第二张卡片
wap-agent card --session ./evidence/session-01 --index 1
wap-agent follow --session ./evidence/session-01 --link 0 --execute
wap-agent back --session ./evidence/session-01
```

`follow --link` 的编号必须来自**当前卡片**的 `links` 数组；上面的 `0` 只是示例。`card --index` 必须来自 `cards[].index`，无须 `--execute`，也不会重新请求网络。首页有多张卡片时，先查看 `card_links[].target_index`，再使用 `card` 进行页内切换；`back` 可以还原此前的卡片或网页。

每次 `open` 或 `follow` 都要明确使用 `--execute`，最多发出一次公开 GET。程序不会自动重定向、跨域跳转、登录、携带 Cookie、提交表单或运行 JavaScript/WMLScript。

JSON 结果包含 `ok`、`url`、`http_status`、`mime`、`format`、`text`、`text_available`、`active_card_index`、`cards`、`card_links`、`links`、`do_links`、`form_preview`、`form_submission_supported`、`sha256`、`cursor`、`page_count` 等字段。非 WML 响应会按失败或非 WML 状态呈现。原始会话可能保存 **Set-Cookie 响应头**，不要公开、提交或分享整个取证目录。

## MCP 接入（本地标准输入输出）

支持 MCP 的 Agent 可以把下面的配置作为本地子进程启动示例（按客户端实际配置结构调整）：

```json
{
  "mcpServers": {
    "wap-probe": {
      "command": "python3",
      "args": ["-m", "wap_probe.agent_mcp", "--allow-network"],
      "env": {"PYTHONPATH": "/ABSOLUTE/PATH/TO/wap-probe/src"}
    }
  }
}
```

启动参数 `--allow-network` 只代表允许联网操作；每次实际调用 `wap_open` 或 `wap_follow` 时仍必须携带 `execute: true`。去掉启动参数即可让 MCP 仅能离线读取。

MCP 提供七项工具：`wap_open`、`wap_follow`、`wap_go`、`wap_read`、`wap_back`、`wap_card`、`wap_form_plan`。其中 `wap_card(session_id, index)` 仅在本地切换已有卡片；不会发送 HTTP 请求。会话使用随机 `session_id` 标识，不允许 MCP 客户端随意提供磁盘路径；服务退出后临时会话自动清理。

本服务为**仅限本地 stdio 的 MCP 2025-11-25 JSON-RPC 工具子集实现**，不宣称支持 Streamable HTTP 或所有可选 MCP 能力；也不会开放监听端口。

## 测试与历史研究

```bash
python3 -m zipfile -e vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip .r5_unpacked
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
  python3 -m unittest discover -s tests -v
```

CI 会验证冻结 R5 SHA-256，并运行现有代码测试及不改动的 **139 项 R5 原测试**。CI 默认**不会访问真实第三方网站**。

相关资料：[Agent 使用说明](AGENT.md) · [R5 冻结来源](docs/R5_SOURCE.md) · [2026 国内 WAP 存活调查](docs/FINAL_FINDINGS_20261029.md) · [真实双页实测记录](https://github.com/Blueteemo/wap-probe/actions/runs/40859035071)。

## 安全边界及项目关系

来自网站的文字始终是不可信的数据，不能作为 Agent 指令执行。本工具只接受公开 DNS 域名，限制响应体大小、验证并绑定公网 IP、禁止自动重定向和凭证操作；不要用于内部或需要认证的系统。

**WAP Probe** 面向本地 Agent 与协议研究；规划中的 **WAPDS** 则是另一个面向 Nintendo DSi 实体掌机的图形化浏览器项目，不混用代码与交付目标。原生 WSP/WDP 暂列独立研究方向，必须通过受控、获授权的网关环境开展。

**许可证：**尚待对历史 R5 源码与依赖完成来源及再分发审核。在审核完成之前不公开发布仓库和冻结归档。

### 实际 MCP 联网验收

[MCP 真实访问验收](https://github.com/Blueteemo/wap-probe/actions/runs/40864597665) 已确认本地 stdio 进程可完成初始化、列出工具，并按 `wap_open → wap_follow → wap_back` 顺序读取书法集 WML 首页和“君”字详情（两次 HTTP 200）。WMLC 中文文本另由冻结 R5 的二进制样本在离线测试中验证。正常 CI 仍不联网。

### 表单结构只读预览（v0.5.0）

读取卡片时，JSON 的 `form_preview` 会列出 WML/WMLC 的 `input`、`select` / `option` 和 `go` / `postfield` 结构：字段类型、选项的显示标签、GET/POST 方法、是否使用变量，以及是否包含预填值。**预填内容、令牌、密码和 postfield 的具体值不提供。** 所有表单的 `submission_available` 都是 `false`，`form_submission_supported` 固定为 `false`；没有提交或构造 GET/POST 请求的接口。即使 WML 的 `go` 写了 `method=get`，也不会混入普通可跟随链接。页面内容仍视为不可信数据。

## v0.6.0：离线 GET 表单请求计划

在当前已验证的 WML/WMLC 卡片中，`wap-agent form-plan` 可以检查 **明确指定的 GET 表单动作**，校验普通输入框、单选项、`postfield` 变量引用、UTF-8 查询编码与同源公开目标，生成脱敏计划。**它不会向网站发送请求，不能提交表单。**

先将要填写的非敏感字段保存在本地 JSON 文件（例如 `{"q":"中国书法","genre":"puzzle"}`），再对已打开且包含相应表单的会话执行：

```bash
wap-agent form-plan --session ./evidence/session-01 --action 0 --values-file ./my-search-values.json
```

结果包含 `request_sha256`、`source_sha256`、`query_keys`、`target_origin`、`path`、`risk` 和 `review_required`，**不会回显提交值，也不保留填写内容**。普通 SHA-256 指纹可能被猜测攻击，不能视作匿名化或授权令牌。`--action` 必须来自当前卡片的 `form_preview.actions`。

MCP 同步提供离线工具 `wap_form_plan(session_id, action, values)`，不需要启用联网权限，但仍不提供表单执行工具。严格拒绝 POST、动态目标 URL、非同源、明显修改状态的路径、敏感字段或路径、复杂变量表达式、未声明或不匹配的选项以及超出限制的请求。现阶段仅支持简单文字输入、单选及 `$(name)` 形式的 GET `postfield`。**GET 可能导致服务端状态变化，计划通过不代表可以安全执行。**

规范与具体约束参见 [GET 表单计划与安全策略](docs/FORM_GET_PLAN.md)。

### v0.6.1｜表单兼容性与安全加固

本轮增加 12 组离线兼容性测试。对重复控件名、`onevent` / `setvar` 等状态操作、选择项 `onpick`、重复选项值、`format` 掩码以及不确定的字符集处理，均采取**无法准确模拟则拒绝生成请求计划**的策略。GB2312 页面只有显式声明 `accept-charset="utf-8"` 时才可进入当前保守的 UTF-8 规划路径。**不开放 GET 表单实际提交**：方法为 GET 并不能保证服务端无副作用。

完整兼容性矩阵及是否开放执行接口的决定见 [WML 表单兼容性报告](docs/FORM_COMPATIBILITY.md)。原有 CLI、MCP 阅读与卡片导航保持不变。

### v0.7.0｜五个历史 WAP 站点实测与传统 `do/go` 导航

本轮五个公开历史 WML 站点的首页与第二页均经实际 Agent 路径验证（HTTP 200）。其中 Blue G 首页采用 GB2312 和传统 `<do><go>` 操作，原有浏览器可以解码但不能访问目标二级页。现在针对**无输入、无脚本、无提交字段**的页面导航提供独立的 `do_links[]` 列表。

与普通链接不同，必须从当前卡片的 `do_links[].index` 选取编号，并显式执行：

```bash
# 仅当当前 WML 页面确实提供 do_links[].index=0
wap-agent go --session ./evidence/session-01 --index 0 --execute
```

MCP 对应 `wap_go(session_id, index, execute: true)`，服务器仍须开启 `--allow-network`。**这不是表单 GET 提交**：POST、`postfield`、动态 URL、WMLScript、明显修改状态的路径及二进制下载不进入可浏览候选。GET 仍可能存在服务端副作用，调用前需确认目标是公开只读页面。

[五站真实兼容性记录](docs/REAL_WORLD_COMPAT_20261029.md)说明网页文本、导航类型和验证边界。五站的 HTTP/WML 实网成功**不代表 WMLC 实网、实体旧手机或 WSP/WDP 已完成验收**。

### v0.7.1｜WMLC 优先协商与二进制 HTTP 回归

新增可选请求画像 `wmlc`，与原来的 `wap1` 使用相同 Nokia 7110 UA，但 `Accept` 优先声明 `application/vnd.wap.wmlc`。旧版 `wap1`、`s60` 和历史调查矩阵保持不变。命令行示例：

```bash
wap-agent open 'http://wap.shufaji.com/' --profile wmlc --out ./evidence/wmlc-sample --execute
```

MCP 的 `wap_open` 同样支持 `profile: "wmlc"`（仍须 `execute: true` 及服务端 `--allow-network`）。**声明希望接收 WMLC，并不代表服务器真的会返回 WMLC。**

五个历史站点的 WMLC 优先实测全部得到文本 WML（其中书法集第一次请求失败，单次复核成功）；本轮 **0/5 获得第三方 HTTP WMLC 响应**。另通过仅限测试环境的本机 HTTP 服务器，验证正确 MIME 的二进制 WMLC 能被 R5 解析为两张包含中文文本的卡片；这属于**受控 HTTP 联调**，不是第三方实网 WMLC 证据。

[完整协商与测试报告](docs/WMLC_HTTP_COMPAT_20261029.md)。不支持 HTML、WMLScript 或泛化的 WBXML MIME 自动识别；未添加 root、代理绕行或自动提交。
