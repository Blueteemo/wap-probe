# WAP Probe — rootless WML reader for Agents

**The original goal is back:** give a local coding Agent a safe, usable interface
to read traditional WML pages, follow a verified public link and inspect
navigation history without root or browser automation.

**Working scope:** direct HTTP(S) WML with UTF-8/GB2312 text, safe same-origin
GET links and JSON output; R5 also validates WMLC decks, though readable WMLC
text and native WSP/WDP are not implemented in the new Agent view.

**[Agent interface and copy-paste commands](AGENT.md)** ·
[2026 survey result](docs/FINAL_FINDINGS_20261029.md) ·
[Research-grade capture](docs/LIVE_CAPTURE.md)

```sh
PYTHONPATH=src python -m wap_probe.agent_browser open \
  'http://wap.shufaji.com/' --out /tmp/wap-visit-1 --execute
PYTHONPATH=src python -m wap_probe.agent_browser follow \
  --session /tmp/wap-visit-1 --link 0 --execute
PYTHONPATH=src python -m wap_probe.agent_browser back --session /tmp/wap-visit-1
```

**Status:** Rootless Agent JSON interface has passed offline unit tests and a
**real two-request public WML browsing smoke test**: [run #40859035071](https://github.com/Blueteemo/wap-probe/actions/runs/40859035071).
It opened the shufaji homepage (HTTP 200, 7 safe links), then followed its
actual /0x541B.wml link (HTTP 200) and extracted readable text.
Native WSP/WDP remains outside the Agent reader's supported scope.
The repository remains private pending license/provenance review.
No sudo, Python third-party dependencies, cookies, auth or automatic crawling.

---

## Historical research and validation infrastructure

WAP Probe 是用于传统 WAP 协议研究、WML/WMLC 解析、HTTP 证据采集与验证、离线回放及互操作测试的 Python 工程。

**当前工程状态：R8 在线 WML 存活调查已结项；8 个重点历史入口中有 5 个取得同源 HTTP/WML 双页证据，且经冻结 R5 和独立 WaveNav 复核。实体旧机／原生 WSP/WDP 仍未测试。**

**[查看 2026-10-29 最终清单、等级与设备兼容性边界](docs/FINAL_FINDINGS_20261029.md)**

**冻结 R5 已入库，R6 离线证据层已接入真实 R5 解析器。** R5 源码及其原有测试保存在不可变 ZIP 归档中，由 GitHub Actions 验证 SHA-256 后解包运行；这不是在线站点的 A 级验收。

## 工程结构

- `vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip`：冻结的原始 R5 工程，包含源码、WBXML/WMLC 测试样本和原有 139 项测试。
- `src/wap_probe/evidence_gate.py`：离线校验 HTTP 响应头、正文、元数据、SHA-256、内容长度及 IP 一致性。
- `src/wap_probe/r5_adapter.py`：读取已验收的 R6 证据，**实际调用冻结 R5 的 `inspect_markup()`**，生成 `r6-r5-export-v1`；过滤需要输入的 WML 导航链接。
- `src/wap_probe/navigation.py`：挑选公开的同源 GET 二级页面候选，不自动发起网络请求。
- `src/wap_probe/bridge.py`：把首页和二级页的证据与 R5 解析结果关联，输出可审计的状态，不会自动授予 A 级。
- `tests/`：R6 单元测试、真实 R5 适配测试，以及离线两页集成测试。
- `.github/workflows/tests.yml`：验证源 ZIP，运行当前 R6 和冻结 R5 测试。仅 main 推送和手动触发，不使用 PR 自动测试。

## 运行测试

Python 3.10+，离线执行，不需要公网连接。首先解包 R5（请先核对 SHA-256，详见 [R5 来源与迁移说明](docs/R5_SOURCE.md)）：

```bash
python3 -m zipfile -e vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip .r5_unpacked
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
  python3 -m unittest discover -s tests -v

for part in probe discovery integrations; do
  (cd ".r5_unpacked/wap-probe-live-discovery-r5/$part" && \
    python3 -m unittest discover -p 'test_*.py' -q)
done
```

当前 GitHub Actions 对提交执行了 **93 项 R6/适配/集成测试 + 139 项冻结 R5 测试，均通过**。这些测试使用预置或合成数据，不是在线网站检测。

## 真实 R5 → R6 离线执行

假设 `evidence/home` 中已经有符合 R6 数据规范的 `metadata.json`、`headers.bin` 和 `body.bin`：

```bash
PYTHONPATH=src python3 -m wap_probe.r5_adapter \
  --capture evidence/home \
  --r5-dir .r5_unpacked/wap-probe-live-discovery-r5/probe \
  --out evidence/home/r5_export.json

PYTHONPATH=src python3 -m wap_probe.bridge \
  --home evidence/home \
  --home-r5 evidence/home/r5_export.json
```

出现 `CHILD_GET_REQUIRED` 只表示已找到可供人工或受控采集器验证的二级 GET 候选；**并不表示已发生请求**。

## 验收和安全边界

- 仅对公开无登录目标进行安全的 GET 请求；HTTP 与 HTTPS 独立，禁止自动跟随重定向。
- `WML_CAPTURED_NEEDS_R5` 表示证据通过字节级检查，但尚待实际解析；`TWO_PAGE_EVIDENCE_MATCHED` 表示两份离线证据/解析出口一致，**不自动授予 A-origin 或 A-navigation PASS**。
- R5 XML/WBXML 解析成功并非完整 WML DTD 一致性或真实设备兼容性证明。
- WAP Labs 网关输出属于单独的互操作证据，不能替代直连原站响应。
- 目前 R6 导航桥接只使用首页第一张卡片上的链接；`#card` 有界可达性遍历与显式启用的真实 HTTP 采集器均已添加。
- CI 不主动访问任何真实 WAP 站点，不启动 Deep Research。

许可证尚未确定，在审核项目来源与再分发条件前不改为公开仓库。

## R6 原站验证（须显式授权联网）

只预览 32 项 HTTP/HTTPS × 两类旧手机 UA 的候选采集矩阵：

```sh
PYTHONPATH=src python3 -m wap_probe.pipeline --matrix
```

在具备直连公网能力的环境中，单站点实际采集和 R5 两页验证：

```sh
PYTHONPATH=src python3 -m wap_probe.pipeline --url http://tx.com.cn/ \
  --profile wap1 --out evidence/tx-wap1 --execute
```

`--execute` 为必选的联网开关；默认仅预览任务。参见 [R6 采集说明](docs/LIVE_CAPTURE.md)。CI 不自动扫描站点；原采集器的 A 级机器字段仍为 PENDING，人工 HTTP/WML 证据分级参见 [最终清单](docs/FINAL_FINDINGS_20261029.md)。


### 2026-10-29: 两处国内 WML 双页实网取证

- **书法集** `http://wap.shufaji.com/`：Nokia 7110 与 S60v3 两种画像均取得首页 HTTP 200 `text/vnd.wap.wml`；由首页真实链接进入 `/0x541B.wml`（“君”字）也为 HTTP 200 WML。HTTPS 独立采集连接超时，不可混称支持 HTTPS。
- **517名站／我要起名网** `http://wap.517ming.com/`：首页及从页面实际链接访问 `/helian-xing.wml` 均为 HTTP 200 `text/vnd.wap.wml`。两站有互相引用的友情链接与按服务器时间变化的“报时”；站点维护者是否仍在更新正文尚未验证。
- **天下网**：HTTPS WML 首页持续有效，但“服务”二级页返回 302 至 HTTP 访客入口，“小说”二级页返回 502；均不能记为可用 WML 二级页面。
- **IP138 历史 `.wml` 路径**：HTTP 301 至 HTTPS；HTTPS 又 302 至 `dnsdblookup.com`，所以当前精确路径没有 WML 取证，不代表整个 IP138 已停运。

取证运行：[第一次四入口](https://github.com/Blueteemo/wap-probe/actions/runs/40846429748)、
[复核与补充](https://github.com/Blueteemo/wap-probe/actions/runs/40846746719)。
原始私有工件仅保留三天，**不可把 Set-Cookie 等原始响应头提交到仓库**。
各站首页与二级页的原始 WML 都通过了冻结 R5 及独立 XML 结构解析，但正式 A-origin/A-navigation 仍标记 PENDING，等待独立 WAP 引擎交叉复核和人工签署。


### R7 独立引擎交叉复核（2026-10-29）

使用 **固定提交 `9cd7ab97dc6752fc1616feb3505a58603f6a45df` 的 WAP Labs／WaveNav Rust 引擎**，对既有 R6 GitHub Actions 工件中的 **6 份原始 WML 正文字节**校验 SHA-256 后进行独立加载、卡片识别及渲染。

- 书法集 `http://wap.shufaji.com/`：Nokia 7110 与 S60v3 画像下的首页和“君”字二级页，共 **4/4 通过**；
- 我要起名网 `http://wap.517ming.com/`：Nokia 7110 画像下的首页和“赫连”姓详情页，共 **2/2 通过**；
- 独立 WaveNav 的 **6/6 加载与渲染均成功**，原始数据 SHA-256 **6/6 一致**；
- 两站已有真实 HTTP 200 + WML 首页与同源子页 GET 记录、冻结 R5 解析记录和本轮独立 WaveNav 记录。可标注为**国内 HTTP WML 双页证据已确认**，但尚非实体设备／原生 WSP/WDP 验收。

独立复核：[Actions #40847596595](https://github.com/Blueteemo/wap-probe/actions/runs/40847596595)；完整验收范围及每页哈希见 [R6/R7 采集说明](docs/LIVE_CAPTURE.md)。这次 **未对目标网站发出新请求**，只重放原有私有证据。

**验收口径：** `A-origin` / `A-navigation` 机器状态仍保留 `PENDING`，直到另外补足所需的传输/设备和最终签署条件；不能把 WaveNav 的离线解析成功外推成 Nokia 实机上网或 WSP/WDP 通过。

### 真实 HTTPS 样本的导航排除策略

2026-10-28 首次 HTTPS 采集得到 `tx.com.cn` 首页 HTTP 200、WML 1.1、6,943 字节并由冻结 R5 解析出一张卡片。首页第一条 `/in/fltin_t.jsp?...type=login` 为登录/注册入口，返回 HTTP 302；它不是公开二级内容的有效验收样本。R6 现在排除明显的登录/注册 URL 路径和操作参数，优先尝试首页后续公开 GET 链接。这不保证后续链接一定返回 WML，二级响应仍需独立验证。访问行为仍限制为 GET、不发送登录表单、不跟随重定向。
