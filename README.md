# WAP Probe

WAP Probe 是用于传统 WAP 协议研究、WML/WMLC 解析、HTTP 证据校验、离线回放及互操作验证的 Python 工程。

**当前状态：R6 离线证据模块初版。R5 原始解析器及历史 139 项回归测试尚未迁入本仓库。**
历史 R5 测试数量仅为既有记录，不能视作本仓库的当前测试结果。

## 已入库的 R6 模块

- `wap_probe.evidence_gate`：离线校验 `metadata.json`、`headers.bin`、`body.bin` 的状态、SHA-256、内容长度、MIME 和公网 DNS/IP 一致性；不会授予 A 级。
- `wap_probe.navigation`：从规范化的 R5 链接中挑选同源 GET 二级页面候选，不触发实际请求。
- `wap_probe.bridge`：核验两页采集证据与规范化 R5 JSON 输出是否对应；**不会调用 R5 解析器，也不能证明 JSON 本身由真实 R5 执行生成**。
- `tests/`：仅使用 Python 标准库的离线回归测试。
- GitHub Actions：在 `push`、`pull_request` 或手动触发时运行语法编译与离线测试，不访问候选 WAP 网站。

## 运行离线测试

Python 3.10+，无需安装外部测试依赖：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

检查一个已有的证据目录集合：

```bash
PYTHONPATH=src python3 -m wap_probe.evidence_gate evidence/
```

已获得一份实际的规范化 R5 输出后，可以生成下一步 GET 计划：

```bash
PYTHONPATH=src python3 -m wap_probe.bridge --home evidence/home \
  --home-r5 evidence/home/r5_export.json
```

如果输出 `CHILD_GET_REQUIRED`，表示**应另行安全采集**，不是已访问或已验证第二页。

## R5 输出适配约定（尚未真实接入）

```json
{
  "schema": "r6-r5-export-v1",
  "status": "ok",
  "strict": true,
  "source_sha256": "<body.bin 的真实 64 位 SHA-256>",
  "cards": [{
    "id": "home",
    "links": [{"href": "next.wml", "method": "GET"}]
  }]
}
```

这里是**约定格式**而非真实站点解析结果。下一阶段须把真实 R5 解析器的严格解析结果接入，并验证生成过程。当前桥接器只从第一张卡片读取链接，以避免误把未到达的隐藏卡片当作首页导航。

## 验收边界

- A-origin 要求：原站独立 HTTP 200 WML/WMLC 原始证据 + R5 严格解析至少一张有效卡片，且实际运行过程可复核。
- A-navigation 要求：上述首页条件成立，且沿首页公开同源 GET 链接完成第二次独立采集与严格解析。
- WAP Labs / 网关的 WSP、WDP 和 WBXML 结果属于独立互操作证据，**不能替代原站直连证据**。
- 永不把 `WML_CAPTURED_NEEDS_R5`、`TWO_PAGE_EVIDENCE_MATCHED` 当作自动 A PASS。
- 全程仅公开目标、只允许 GET、禁止登录和自动重定向。**当前仓库不包含任何自动外网采集 CI。**

## 后续工作

1. 核验本仓库的首次 GitHub Actions 回归结果，并修复实际失败。
2. 迁入已验证的 R5 解析器及既有测试，再完成 R5→R6 实际调用适配。
3. 在充分的 SSRF / DNS 绑定 / HTTP framing 测试后，另行实现受控、手动运行的 R6 采集器。
4. 真实采集成功后再讨论 A-origin / A-navigation 验收与扩展。

License 暂未确定，公开前再核对来源和授权。
