# WMLC HTTP compatibility & negotiation — 2026-10-29

**Version 0.7.1 · Private research note · No third-party live WMLC response confirmed.**

## What was tested

Added a third, explicitly selected `wmlc` device profile with the Nokia 7110 user agent but a WMLC-first `Accept: application/vnd.wap.wmlc,text/vnd.wap.wml;q=0.7,*/*;q=0.1`. Existing `wap1` and `s60` request profiles and the original 32-request historical research matrix remain unchanged. This is content negotiation, **not a converter, transcoder, WSP/WDP gateway or a promise that the origin supports WMLC**.

Used the actual opt-in rootless Agent `open_page(..., profile='wmlc')` through five known public anonymous historic WML homes; one HTTP GET per site, without credentials, cookies, redirects, forms, or download activity. Printouts included only HTTP code, verified MIME, R5 parse status, card/text counts, and SHA-256. No raw headers or body were published.

### Direct-origin observations

| Site | WMLC-preferred HTTP result | Evidence classification |
| --- | --- | --- |
| `http://wap.shufaji.com/` | First attempt failed before response (`HTTP 0`); **one targeted retry HTTP 200, `text/vnd.wap.wml`, 1,543 bytes** | Text WML, **not** WMLC |
| `http://wap.517ming.com/` | HTTP 200, `text/vnd.wap.wml` | Text WML, verified R5 |
| `http://wap.ee1234.com/` | HTTP 200, `text/vnd.wap.wml` | Text WML, verified R5 |
| `http://wap.uc123.com/` | HTTP 200, `text/vnd.wap.wml` | Text WML, verified R5 |
| `http://wap.yuyangzhou.name/` | HTTP 200, `text/vnd.wap.wml` | Text WML, verified R5; GB2312 content |

First-pass run [#40882223817](https://github.com/Blueteemo/wap-probe/actions/runs/40882223817), single-host retry [#40882388958](https://github.com/Blueteemo/wap-probe/actions/runs/40882388958). The result is **5/5 sites with valid text WML in the sampled requests; 0/5 confirmed direct-origin WMLC MIME responses**. Do not extrapolate to all public WAP servers or allege they *never* serve WMLC under any device profile.

### Controlled binary HTTP transport (not a third-party site)

Offline CI now runs a loopback-only `127.0.0.1` HTTP server serving the frozen R5 `binary_portal.wmlc` sample with `Content-Type: application/vnd.wap.wmlc`. The test performs a real HTTP GET over loopback and verifies the exact response octets, MIME, two cards and Chinese text via the unmodified R5 decoder. Additional tests reject a misleading `text/html` MIME, truncated binary bytes and HTTP redirects. This is valuable **transport-to-parser verification**, but **not** production `collector.capture` evidence, public DNS evidence or an external WMLC site.

Production still forbids IP literals, nonpublic DNS results, proxy bypass, automatic redirects, TLS bypass, cookies, logins, POST, and form execution. The loopback server is only constructed inside tests and never added to the production allowlist.

## Remaining limitations and next investigation

- A genuine anonymous, public HTTP origin returning a WMLC entity with its correct MIME remains **unverified**. Do not label the repository as third-party WMLC-live validated.
- WAP Labs independently hosts a public first-party interoperability service at `wap://interop.wap.shrimpworks.dev/` through a connectionless WSP/WDP gateway, **not** an authenticated direct HTTP URL. We did **not** access the gateway in this round, nor did we reuse its gateway or WMLC output as proof for our HTTP collector. Refer to its [public lab documentation](https://github.com/dills122/wap-labs).
- A next legitimate step, if needed, is to work with a controlled first-party origin serving deterministic WMLC over ordinary public HTTP and obtain permission for a single public test GET. This should remain separate from the historical Chinese-WAP survival census.
- This round does not establish compatibility with every WBXML code page, WMLScript, real vintage Nokia, Nintendo DSi, or native WSP/WDP.

## Standards and interpretation

OMA WAE media type specifications distinguish the textual WML1 media type `text/vnd.wap.wml` from binary WML1 `application/vnd.wap.wmlc`. A `.wmlc` file extension or the client's `Accept` header alone is **not** proof the received payload is compiled WML. See [OMA WAE specification](https://www.openmobilealliance.org/tech/affiliates/wap/wap-236-WAESpec-20011109-a.pdf) and [IANA WMLC media-type registry](https://www.iana.org/assignments/media-types/application/vnd.wap.wmlc).

**Workflow hygiene:** temporary one-shot negotiation and retry workflows were retired after their runs; the permanent offline test workflow and opt-in manual origin sample remain.
