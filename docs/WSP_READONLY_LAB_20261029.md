# WSP/WDP 只读实验链路｜WSP/WDP Read-only Lab Validation

**2026-10-29 · WAP Probe v0.8.0 · Separate experimental transport**

## 核验结论 / Verified outcome

A real connectionless WSP GET was sent over UDP to **WAP Labs' publicly advertised first-party interoperability gateway**. A genuine WSP Reply was received and successfully decoded via frozen R5:

| Property / 项目 | Observed / 实际结果 |
| --- | --- |
| Public gateway / 公开网关 | `159.89.254.0:9200` (WAP Labs' published test address at test time) |
| Logical resource / 目标资源 | `http://interop.wap.shrimpworks.dev/` (mapped from WAP Labs' public `wap://interop...` resource) |
| WDP bearer / WDP 承载 | IPv4 UDP, connectionless, one datagram GET |
| Reply PDU | `0x04`, matched transaction ID |
| WSP status / 状态 | **200 (WSP-mapped, not an HTTP response)** |
| WSP content type | `application/vnd.wap.wmlc` |
| Body size / 响应体 | **235 bytes** |
| Body SHA-256 | `cb0f2e170f875f35d55e80943c6e491e72e3b875a32c3783fcdb29257eb5448b` |
| Frozen R5 | **1 card**, readable English first-party interoperability text |

GitHub Actions one-shot actual network test: [run 40887346599](https://github.com/Blueteemo/wap-probe/actions/runs/40887346599), log marker `WSP_LAB_SINGLE_GET_EXIT=0`. This result was reached without HTTP proxying, curl, POST, credentials, cookies, scripts, follow-up navigation, or WTLS.

**Important distinction / 重要区别：** This is a real **public first-party interoperability test service** intentionally offered by WAP Labs, not an original historical Chinese WAP website or general carrier gateway. It does prove a narrow WSP/WDP → WMLC → R5 card-text path can work over a real network. It does **not** prove broad WSP/WDP compatibility, authentic vintage handset/browser equivalence, or true end-to-end WTLS security.

## Architecture / 架构

`src/wap_probe/wsp_readonly.py` is a separate, standard-library-only experimental client. It does not modify HTTP `collector.capture`, the `wap-agent` session format, the seven MCP tools, R5, nor any WML form rules.

- Pure `encode_get()` and `decode_reply()` functions implement bounded WAP-203 connectionless GET and Reply, with uintvar URI length, one WMLC or WML Accept field, transaction-ID correlation, status mapping and minimal content-type handling.
- Public UDP transport is restricted to the **single hard-coded published gateway and the single anonymous interop homepage**, not arbitrary destination URLs, ports or general UDP probing. Two explicit CLI flags are required.
- Single GET, single datagram, 4-second socket timeout, no automatic retries/redirects. Receiver checks peer association (connected UDP socket), transaction ID, PDU type, WSP status, bounded header length, MIME and payload size before passing bytes to frozen R5.
- `--allow-network` and `--execute` must both be present. The default command cannot open a socket.
- No secrets are used. A public unencrypted shared UDP gateway is **not** appropriate for credentials or private traffic. UDP peer filtering and a random one-byte transaction ID **are not cryptographic authentication**.

## Usage / 使用

From the checked-out private repository with `vendor/r5/`:

```bash
# inspect help; does not perform any network action
PYTHONPATH=src python3 -m wap_probe.wsp_readonly --help

# one explicit public first-party lab GET; unencrypted UDP
PYTHONPATH=src python3 -m wap_probe.wsp_readonly --lab --allow-network --execute
```

Editable install also provides `wap-wsp-lab` with identical flags. No `wap-agent open` or `wap-mcp` WSP mode has been added.

## Independent offline vectors / 独立对照

Source: [WAP Labs/Lowband WSP connectionless matrix](https://github.com/dills122/wap-labs/blob/9cd7ab97dc6752fc1616feb3505a58603f6a45df/transport-rust/tests/fixtures/transport/wsp_connectionless_matrix/matrix_fixture.json), fixed upstream commit `9cd7ab97dc6752fc1616feb3505a58603f6a45df`, MIT license, © 2026 Dylan Steele. This is an excerpt of GET, Reply, assigned statuses and malformed test vectors only; no POST implementation was copied. Source attribution and notice: `tests/fixtures/LOWBAND_LICENSE.txt`.

Offline regression coverage under `tests/test_wsp_readonly.py` includes:

- Independent **byte-for-byte** GET encoding and Reply decoding, WSP status assignments and uintvar boundaries
- Truncated, wrong-type, wrong-ID and unknown-content-type PDU rejection
- Two-flag network authorization with a check that no socket opens by default
- **Actual localhost UDP GET and WMLC Reply** containing the frozen Chinese binary fixture; R5 reads two cards
- Wrong transaction ID and one-datagram timeout, without retries

The normal CI runs these locally **without accessing any public WSP gateway**. An ephemeral GitHub Actions public gateway acceptance workflow was used once and **removed**.

## What this is not / 非目标

No WTP connection mode, WTLS, WCMP, WDP fragmentation/reassembly, arbitrary gateways, private IP targets, cookies, sessions, redirects, retransmission strategy, commercial carrier networks, HTML renderer, form submission, WMLScript, or general WAP website navigation. The parser remains the exact frozen R5 archive; license/provenance review for that historical archive still blocks treating the whole private repository as approved public open source.

Further expansion would first need independent header/charset forms, WDP fragmentation handling, and an explicit per-origin allowlist review. Avoid making the currently bounded lab client an unrestricted WAP network client.
