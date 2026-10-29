# v0.8.2｜WSP 原始报文证据与离线 Agent 导入

**Scope:** single allowlisted WAP Labs connectionless WSP GET/Reply; offline import and Agent card reading only. Frozen R5 remains unchanged.

## 成果

v0.8.0 已通过真实公开互操作网关 GET 验证，v0.8.1 增加 WSP MIME/charset 解析。本轮 **没有再次请求第三方网关**；新增功能由固定报文和本机 UDP 回环测试支持。

新增 `src/wap_probe/wsp_evidence.py`，将独立 WSP 实验客户端返回的**原始 GET/Reply PDU**保存成独立证据，拒绝伪造 HTTP/curl 取证格式。Agent 新增 `import-wsp` **离线导入**入口，可对固定公开实验资源的 WML/WMLC 响应，调用原始冻结 R5 生成只读本地卡片会话。

## 工作流程

```bash
# 1. 仅针对固定的 WAP Labs 匿名互操作测试站，明确允许一次 UDP GET；
#    --evidence-out 额外要求一个尚不存在的文件夹，绝不覆盖旧证据。
wap-wsp-lab --lab --allow-network --execute \
  --evidence-out ./evidence/wsp-lab-original

# 2. 以下操作全部离线，不调用 UDP、curl 或任何网站。
wap-agent import-wsp \
  --evidence ./evidence/wsp-lab-original \
  --out ./evidence/wsp-lab-session
wap-agent read --session ./evidence/wsp-lab-session

# 3. 只有 read 返回 cards[] 确有 index=1 才切卡。
wap-agent card --session ./evidence/wsp-lab-session --index 1
wap-agent back --session ./evidence/wsp-lab-session
```

也可以在没有公开网关的环境中，把本机 UDP 回环测试生成的测试记录导入 Agent。**正式联网抓取默认不保存报文，必须显式提供 `--evidence-out`。**

## 原始证据和会话结构

`evidence/wsp-lab-original/`:
- `request.wsp`：原始单次连接less WSP GET PDU
- `reply.wsp`：原始 WSP Reply PDU，可能包含额外不透明 WSP 头
- `wsp_manifest.json`：严格格式标识、固定实验网关和资源标识、报文字节数、SHA-256、`authenticated: false`

`evidence/wsp-lab-session/`:
- `session.json`：现有 Agent 会话架构，新增 `transport: "wsp-offline"`
- `pages/page-0001/`：复制的原始 WSP 报文与清单、R5 导出的 `body.bin` 和 `r5_export.json`

**不生成** `headers.bin`、`metadata.json` 或虚假的 `HTTP 200`，也不将 WSP 结果送进 HTTP R6 取证门。显示的是 `wsp_status: 200` 和 `http_status: null`。

## 完整性和安全边界

1. 导入前验证清单结构、源网关/逻辑 URI、文件限额与 SHA-256、`GET` 的精确线缆字节、事务 ID 匹配、WSP Reply 类型、状态码、MIME 及非空正文。
2. 冻结 R5 只接受实际可解析的 WML/WMLC，生成卡片、文本、局部 `#card` 目标与脱敏表单结构。
3. **每次读取导入会话**都会重新验证原始 WSP 证据和派生 `body.bin`，重新运行冻结 R5，并核对保存的 R5 导出；恶意修改显示正文不能通过。
4. 离线 WSP 会话 `links[]`、`do_links[]` 均为空，只能离线 `read`、`card`、`back`。拒绝 `follow`、`go` 和表单 GET 规划；没有 WSP 联网续页，也没有额外 MCP 工具。
5. HTTP Agent、MCP 七项工具和历史 R6 HTTP 取证规则原样保留；无 root、代理、脚本、POST、Cookie、认证或 WTLS。

**关于“取证”的含义：** PDU 原件、哈希与长度可校验**本地保存后未被意外改变**，但清单可以由本机用户自行构造或同时篡改，UDP 事务 ID 与服务器端口也不是密码学来源证明。返回的 `source_authenticated: false` 明确提示**未认证网关身份，不具备第三方可信时间戳、签名或链上不可篡改证明**。不要把它当作司法鉴定、运营商身份认证或经过验证的历史 WAP 原站证据。

## 测试与限制

`tests/test_wsp_evidence.py` 覆盖：受控二进制 WMLC 保存/导入、Agent 两卡阅读与离线返回、CLI 无授权读取、目录不覆盖、报文/清单/正文/导出篡改拒绝、异源 GET 与错误事务 ID、R5 解析不通过、链接/表单联网禁止、**真正本机 UDP 往返保存后离线导入**。正常 CI 永不联系公开 WAP Labs 网关。

当前仅一份公开实验首页的单页 WSP 证据；未实现 WSP 新请求、网关发现、WDP 分片、WTP 会话、WTLS、通用 WSP 响应头执行、历史 WAP 原站浏览或将本地文件路径开放为 MCP 导入接口。独立的原版 R5 ZIP 与其 139 项原始测试没有修改。

详见 [v0.8.0 公开互操作网关实网验证](WSP_READONLY_LAB_20261029.md)和 [v0.8.1 响应头与字符集](WSP_HEADERS_CHARSET_20261029.md)。
