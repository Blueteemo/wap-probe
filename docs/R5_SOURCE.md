# Frozen R5 source and R6 integration

The original, full R5 archive is tracked at:

`vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip`

Expected SHA-256:

`cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa`

This is intentionally **unmodified** so the 2026-10-28 frozen source, binary WMLC fixtures, nested historical test archive, and 139 original test cases remain reproducible. The GitHub Actions job verifies SHA-256 before extracting into ignored `.r5_unpacked/`. Do not edit or silently regenerate the frozen ZIP.

At runtime, `frozen_r5()` verifies the complete immutable R5 ZIP SHA-256 but extracts **only** `probe/wap_probe.py` and `probe/wap_wbxml.py` into an ephemeral user-space directory. Nested historical reviews, captured WML, logs and other archived research material are **not** unpacked for ordinary Agent reading. The original archive remains unchanged.

The new `src/wap_probe/r5_adapter.py` directly imports the real R5 parser (`probe/wap_probe.py` / `probe/wap_wbxml.py`), analyzes previously captured bytes, and produces a normalized `r6-r5-export-v1` for R6 bridge. Links with R5's `requires_inputs` flag are excluded from automatic GET candidates.

The tests under `tests/test_r5_adapter.py` run against the actual frozen R5 parser. `tests/test_r5_bridge_integration.py` feeds **synthetic, labeled** HTTP captures through R6 evidence gate, actual R5 parser, then R6 bridge. They are not proof of a live Chinese WML origin, nor native WSP/WDP or physical handset compatibility.

Current design: R6 safely traverses reachable WML `#card` references to plan one same-origin GET. The Agent reader exposes bounded decoded WMLC card text from the frozen R5 parser, with raw-response SHA-256 provenance. R5 is unchanged. No WMLScript, form POST, native WSP/WDP, or physical handset support is implied. Never substitute R5's historical crawler for the no-redirect, pinned-public-IP R6 collector.

Local tests:
```sh
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
python3 -m unittest discover -s tests -v
```

## Public redistribution status (2026-10-30)

The immutable ZIP contains research fixtures, third-party origin response snapshots and one nested historical DeepSeek review archive in addition to the two runtime parser modules. There are **24 main R5 Python sources, 10 nested historical Python source versions, and 10 macOS AppleDouble metadata entries mistaken for source by filename-only scanning**. These are not 44 separate Python implementations. The live runtime now extracts only two parser modules, but shipping the full archive still redistributes all archived evidence. See [the consolidated publication review](PUBLICATION_READINESS_20261029.md) before assigning a root license or releasing the archive publicly.


## 原始研发日志的进一步佐证（2026-10-30）

本轮直接读取了冻结 ZIP 内的 `probe/RESEARCH_LOG.md` 与 `probe/wap_wbxml.py`，而不再只依赖外部报告推断：

- v0.3 研究日志明确记录其作者按照 WBXML/WML 标准、OMA 公共标识及 Android kXML `Wml.java` 的 WML token 对照表开发严格子集解码器；源码头部也直接标注了该参考来源。这支持“项目自主实现解析逻辑、参考标准和既有数值表”的来源解释，但仍不构成独立的源码相似性鉴定。
- 同一日志明确记录自行构造一份 **86 字节、两张卡片、包含 `#next` 页内链接的 WMLC 测试样本**；冻结 ZIP 中 `probe/fixtures/binary_portal.wmlc` 正好为 86 字节。此记录为精简候选保留这份样本提供了清楚的项目起源线索，但仍需要所有者确认原创/模型辅助成果的授权。
- Android kXML `Wml.java` 的数字令牌表与 [WAP Forum WML 规范](https://www.wapforum.org/what/technical/spec-wml-19990616.pdf) 对应；kXML2 的 [上游许可证](https://github.com/kobjects/kxml2/blob/master/license.txt) 为宽松授权，其相邻 [`Wbxml.java` 源文件](https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/Wbxml.java) 带有 Stefan Haustein 的版权及许可声明。协议定义的数值对应不等于证明复制了受保护的实现表达；如果核对发现确实引用了可受保护的表达，应遵循具体许可证和署名条件。

现在精简候选生成器会在候选目录附带 `THIRD_PARTY_REFERENCES.md`，列出上述依据和仍需确认的权利边界。它是**参考来源记录，不是项目 LICENSE 或公开授权**；候选仍标记 `publication_authorized=false`。完整冻结 R5 ZIP 的散列和历史研究数据均不变。

## 公开时的版权/许可边界（拟稿，尚未授予许可证）

原始 R5 ZIP 必须保持字节级不变。它既包含本项目研发的 Python 解析器，也封装了来自公共网站的历史 HTTP/WML/HTML 响应、Kannel 测试参考页，以及由第三方工具采样的资料。因此不能把 **整个 R5 压缩包**一概声明为项目 MIT 授权内容。对任何项目自有代码的 MIT 授权，只覆盖所有者依法有权授权的部分。

- **项目实现**：`src/wap_probe/`、`scripts/`、自编测试、文档以及 R5 中的原创 Python 实现，需最终由所有者确认权属和 MIT 署名后才能授权。R5 原作者研发日志记录 `wap_wbxml.py` 是依据标准、OMA 标识及 kXML 的 token 表编写的严格子集解码器，86 字节两卡片 WMLC 样本为项目构造。
- **第三方测试样本**：`tests/fixtures/lowband_wml13_reference.json` 与 `lowband_wsp_reference.json` 引用固定的 WAP Labs/Lowband 参考向量，已经附上 `tests/fixtures/LOWBAND_LICENSE.txt` 和原提交/路径信息。其许可仍为第三方 MIT，不用新项目署名覆盖原署名。
- **标准和 token 参考**：WML/WBXML 公开标准的数字分配不必然等同复制 kXML 源代码表达；项目已记录 [Android kXML WML token 表](https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/wml/Wml.java) 作为参考。若确认复用了上游受保护表达，保留其原许可证和版权声明，而不能用本项目 MIT 取代。
- **历史外站响应**：嵌套研究 ZIP 中记录了 27 份响应实例（去重后 15 种）及两个外部 Kannel WML 参考文档。没有检测到常见认证凭据，不等于拥有这些第三方页面的再分发许可。它们不属于项目 MIT 拟授权范围。

本章节是仓库公开前的来源声明草稿，不是法律结论，也不是对外部网页的授权。完整历史保留策略已得到确认，但仓库从 Private 切成 Public 仍须所有者最终明确批准。
