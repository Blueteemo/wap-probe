# WAP Probe

WAP Probe 是用于传统 WAP 协议研究、WML/WMLC 解析、HTTP 证据采集与验证、离线回放及互操作测试的 Python 工程。

**当前工程状态：冻结 R5 已入库，R6 离线证据层已接入真实 R5 解析器。** R5 源码及其原有测试保存在不可变 ZIP 归档中，由 GitHub Actions 验证 SHA-256 后解包运行；这不是在线站点的 A 级验收。

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

`--execute` 为必选的联网开关；默认仅预览任务。参见 [R6 采集说明](docs/LIVE_CAPTURE.md)。CI 不自动扫描站点；所有 A 级结论仍为 PENDING，直到人工复核真实采集证据。

### 真实 HTTPS 样本的导航排除策略

2026-10-28 首次 HTTPS 采集得到 `tx.com.cn` 首页 HTTP 200、WML 1.1、6,943 字节并由冻结 R5 解析出一张卡片。首页第一条 `/in/fltin_t.jsp?...type=login` 为登录/注册入口，返回 HTTP 302；它不是公开二级内容的有效验收样本。R6 现在排除明显的登录/注册 URL 路径和操作参数，优先尝试首页后续公开 GET 链接。这不保证后续链接一定返回 WML，二级响应仍需独立验证。访问行为仍限制为 GET、不发送登录表单、不跟随重定向。
