# WSP Content-Type、字符集与响应头边界｜WSP Header and Charset Compatibility

**2026-10-29 · v0.8.1 · Offline-tested / 离线回归验证**

## 背景 / Scope

The v0.8.0 standalone connectionless WSP lab probe could decode short-integer media tokens and simple text strings only. v0.8.1 adds a conservative, independently checked **Content-Type parser**, including WSP *general-form* media/charset parameters, without changing the established HTTP Agent, the seven MCP tools, or the immutable frozen R5 parser.

本次不重新探测公开 WAP Labs 网关。上一版公开实网 UDP/WSP 200 与 235 字节 WMLC 证据仍以 [v0.8.0 的实验记录](WSP_READONLY_LAB_20261029.md)为准；**本轮新增能力由固定报文与本机真实 UDP 回环测试支持，尚未对第三方网关新字符集响应进行实网验证。**

## Implemented / 已支持

| Wire representation / 格式 | v0.8.1 behavior |
| --- | --- |
| WSP short-integer media token, e.g. `0x94` | `application/vnd.wap.wmlc` |
| NUL-terminated text media name, optional `0x7F` quote | Exact allowlisted MIME types only |
| Content-Type general form, short value length | Supports bounded media value and one charset parameter |
| Content-Type general form, `0x1F` + uintvar length | Supports validated uintvar length |
| Charset parameter `0x81`, known MIB value `0x83` | `us-ascii` |
| Charset parameter `0x81`, known MIB value `0x84` | `iso-8859-1` |
| Charset parameter `0x81`, known MIB value `0xEA` | `utf-8` |
| Charset parameter as bounded NUL-terminated text | Only the three names above |
| Opaque WSP headers after Content-Type | Counted and excluded from body; **not interpreted, replayed or displayed** |
| Charset propagation | Forwarded as `mime; charset=...` to frozen R5, without editing R5 |

Returned lab JSON now includes `charset` (null or a recognized name) and `extra_header_bytes` (count only). Raw optional header bytes are **not** returned. `WspReply` stores only status, content-type, raw entity body, recognized charset, and extra-header byte count.

## Security boundaries / 安全边界

The parser rejects oversized/truncated header sections, invalid length encoding, unsupported media types, unknown charset MIB values, malformed text strings, excess/unknown Content-Type parameters, wrong transaction ID, non-Reply PDUs and unsupported WSP status codes. It does **not** silently pick UTF-8 for an explicitly unknown charset.

An accepted WSP header **does not authorize** its extra fields: `Set-Cookie`, `Location`, authentication-related or unknown binary headers (if present) stay opaque and are not sent back or followed. No WSP session state, WTLS, authentication, POST, arbitrary UDP target, cookie jar, general WDP reassembly, or Agent integration is provided.

The public laboratory remains fixed to the single documented WAP Labs interop endpoint, requires `--lab --allow-network --execute`, uses one UDP datagram with bounded timeout, and must never be used for private data. A random one-octet transaction ID and UDP peer association are **not cryptographic authentication**.

## Verification / 验收

- `tests/test_wsp_readonly.py`: **7 new** focused tests (in addition to v0.8.0 coverage). Exercises short and general forms, `0x1F` long-length form, text charset and quote, unknown/malformed parameters and opaque header boundaries.
- Real **localhost UDP** response with `text/vnd.wap.wml; charset=iso-8859-1` and non-ASCII `café` text is parsed end-to-end by the unchanged R5 decoder.
- Existing pinned [Lowband reference WSP matrix](https://github.com/dills122/wap-labs/blob/9cd7ab97dc6752fc1616feb3505a58603f6a45df/transport-rust/tests/fixtures/transport/wsp_connectionless_matrix/matrix_fixture.json) remains a byte-for-byte GET/Reply baseline. The new general-form behavior follows the independently reviewed [Lowband connectionless codec](https://github.com/dills122/wap-labs/blob/9cd7ab97dc6752fc1616feb3505a58603f6a45df/transport-rust/src/network/wsp/connectionless.rs) (not vendored).
- The frozen R5 archive retains its own independent SHA-256 verification and **139 original tests**.

## Not claimed / 未宣称

This is a **conservative subset**, not a full WSP parameter registry, all possible WBXML/charset codes, general header parsing, DTD conformance, device display equivalence, or production WDP/WSP interoperability. Other WSP headers remain opaque by design. The earlier public lab success is real but does not substitute for testing each newly supported charset form with a remote server.

No temporary live workflow was introduced in v0.8.1; regular CI runs offline only. The repo stays private while historic bundled R5 provenance is unresolved.
