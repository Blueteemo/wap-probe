# WAP Probe

**无需 root 的本地 Agent WML/WMLC 只读阅读工具。**

简体中文 | [English](README.en.md)

提供 JSON CLI、本地 MCP stdio 接口和独立的受控 WSP/WDP 实验工具。可读取公开 WML 页面、解析已覆盖的 WMLC/WBXML code page 0 内容、切换卡片，并逐步跟随经过验证的同源链接。

## 安装

需要 Python 3.10+、`curl` 和包含 `vendor/r5/` 的完整源码检出或 Git 源码归档。普通用户权限即可。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/smoke_clean_install.py
```

不要仅分发缺少 R5 源码归档的 wheel。安装冒烟使用合成数据，不访问外部网站。

## 使用

```sh
wap-agent --help
wap-mcp --help
wap-wsp-lab --help
```

以下 `wap.example.org` 是占位域名，请换成你有权访问的公开匿名 WML 页面：

```sh
wap-agent open 'http://wap.example.org/' --out evidence/session-01 --execute
wap-agent read --session evidence/session-01
# 只使用上一步实际返回的 links[].index：
wap-agent follow --session evidence/session-01 --link 0 --execute
wap-agent back --session evidence/session-01
```

离线卡片切换使用 `card --session ... --index ...`。无输入 `<do><go>` 导航使用独立 `go` 命令。表单结构预览和 GET 请求计划均不提交表单。

MCP 客户端以 stdio 子进程启动 `wap-mcp`；允许显式联网工具时添加 `--allow-network`。共 8 项工具，参数及边界见 [AGENT.md](AGENT.md)。

## 功能边界

- 每一步最多一个显式公共 HTTP(S) GET；校验公网 DNS/IP、绑定解析结果、校验 TLS，不自动跟随重定向，不发送凭据或 Cookie。
- WML/WMLC 是语义文本阅读视图，支持已覆盖的卡片、正文、链接及只读表单预览；不是图形浏览器或完整 WML/WBXML 标准实现。
- 不支持 HTML 渲染、WMLScript、变量求值、表单提交、登录态、自动爬取。
- WSP/WDP 是单独显式启用、限定端点的无连接实验；不提供通用运营商网关、WTP 或 WTLS，不代表诺基亚等实体手机兼容。
- 历史实网结论只代表当时采样，不能保证今天的站点或网关仍可访问。
- 采集目录可能包含原始响应及 Set-Cookie，请保留在本地，勿提交到 Git。

## 测试与来源

运行当前项目测试前，可将已固定校验值的 R5 源码包解压到 `.r5_unpacked`：

```sh
python3 -m zipfile -e vendor/r5/R5_Public_Runtime_Test_Sources.zip .r5_unpacked
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
 python3 -m unittest discover -s tests -v
```

R5 三个子目录的独立回归及校验流程见 `.github/workflows/tests.yml`。7 项依赖私人历史外站证据的用例明确跳过，不能记为通过。

完整历史外站正文及研究原件保存在私人备份，不随此源码包分发。[R5 来源与边界](docs/R5_SOURCE.md) · [第三方来源和许可证](THIRD_PARTY_NOTICES.md) · [研究结论](docs/FINAL_FINDINGS_20261029.md)。

项目自有源码的 MIT 许可仍待所有者最终授权；第三方材料遵循各自声明，不由项目许可覆盖。

当前正式发布状态及尚待处理事项见 [发布状态](docs/PUBLICATION_STATUS.md)。
