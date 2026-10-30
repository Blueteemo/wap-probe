# WBXML/WML 1.3 独立参考样本验证｜Independent Reference Verification

**2026-10-29 · WAP Probe v0.7.2 · 离线兼容性研究 / Offline compatibility research**

## 摘要 / Summary

本轮从开源项目 [WAP Labs / Lowband](https://github.com/dills122/wap-labs) 的 Rust WBXML/WML 1.3 符合性测试语料中选取 **23 个固定样本**，对照冻结 R5 解码器输出，不修改 R5 源码。

From Lowband's independently maintained Rust WBXML conformance fixture definitions, **23 pinned cases** were selected and checked against the frozen R5 decoder. The Rust runtime was **not** built or executed in the regular `wap-probe` CI; this is a comparison against **independent checked-in expected outcomes**, not a dual-runtime differential fuzz test.

| 检查项目 / Check | 结果 / Result |
| --- | --- |
| 独立原始语料 / Original Lowband fixture inventory | 42 |
| 本次选取 / Pinned subset | **23** |
| 参考有效 WBXML / Valid reference cases | **12/12 R5 accepted** |
| 参考无效 WBXML / Invalid reference cases | **11/11 R5 rejected** |
| 有效样本中的结构、卡片文本及非默认属性 / Semantics after known DTD-default normalization | **12/12 matched** |
| 原始 XML 字符串完全一致 / Exact XML output string equality | **0/12; not an appropriate pass criterion** |

## 为什么 XML 字符串不同 / Why raw XML differs

Lowband 的参考输出按 WML 1.3 DTD **补入默认属性**，而冻结 R5 的输出倾向于保留更简洁的显式属性。例如 `<card id="main">` 的默认属性 `newcontext="false"` 和 `ordered="true"` 由 Lowband 补全；`<p>` 也可包含默认 `align="left"`。原始 XML 不相同，因此不能声称两套实现具备完整 XML/DTD 字节级一致性。

For this corpus, the reference Rust XML includes implicit WML DTD defaults not inserted by frozen R5. The regression test compares element structure, text, and **non-default** attributes after **only explicitly enumerated WML defaults** are normalized. This is a deliberately limited **Agent-reading semantic comparison**, not a proof of full WML DTD semantics, identical rendering, or byte-for-byte decoder parity.

## 测试覆盖 / Tested categories

- 二进制与 literal 标签/属性等效形式 / Binary and literal tags/attributes
- 字符串表、inline 字符串、数值实体 / String-table references, inline strings, entities
- UTF-8、US-ASCII 和 Latin-1 字符集 / UTF-8, US-ASCII, Latin-1
- WML 默认属性、扩展变量与 token 切换 / Default attrs, extension variables, token context
- 不支持/未知字符集、截断的头部/字符串表/opaque / Unsupported charset, truncated header/string table/opaque
- 非法 literal offset、未分配或保留的 code page / Invalid string-table offset and unassigned/reserved code pages

## 溯源与许可 / Provenance and licensing

- Upstream: `dills122/wap-labs`, commit `9cd7ab97dc6752fc1616feb3505a58603f6a45df`
- Source: [`transport-rust/tests/fixtures/transport/wbxml_wml13/conformance.json`](https://github.com/dills122/wap-labs/blob/9cd7ab97dc6752fc1616feb3505a58603f6a45df/transport-rust/tests/fixtures/transport/wbxml_wml13/conformance.json)
- Curated pinned subset: `tests/fixtures/lowband_wml13_reference.json` (hex and independent expected result only)
- License: Lowband **MIT**, copyright © 2026 Dylan Steele; full notice `tests/fixtures/LOWBAND_LICENSE.txt`
- Frozen R5 remains unmodified, protected by its original SHA-256 check. The repository's **overall redistributable license is still pending** the historical R5 provenance review.

不引用 Lowband 另一组明确标记为 *unvetted robustness corpus* 的 `transport-rust/wbxml_samples/` 文件来冒充规范参考数据。

Do not relabel the separate unvetted `wbxml_samples/` corpus as standards conformance evidence.

## 复现 / Reproduction

需完整源码及冻结 R5 归档：

```bash
python3 -m zipfile -e vendor/r5/R5_Public_Runtime_Test_Sources.zip .r5_unpacked
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
  python3 -m unittest discover -s tests -p 'test_lowband_reference.py' -v
```

Normal offline CI includes these regressions, the other Agent tests and 139 original frozen R5 tests. There are no required remote servers, external Rust/Cargo builds, or network requests.

## 明确未证实的部分 / Not established

- 没有通过本轮验证第三方 HTTP WMLC 源站；先前五个历史网站均返回普通 WML。
- 没有运行两份解码器的实时差分 fuzz、全部 42 个上游样本、完整 WML DTD 验证、渲染一致性或每一种 WBXML charset/page。
- 没有使用原生 WSP/WDP、WAP Labs 公开 UDP 网关或诺基亚真机。

This improves independent **offline compatibility evidence**, not live third-party WMLC availability or complete WAP 1.x conformance. Future expansion should add carefully scoped, independently expected fixtures rather than turning on arbitrary POST, WMLScript or unverified gateways.
