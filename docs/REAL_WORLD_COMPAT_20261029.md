# Real-world WML Agent compatibility — 2026-10-29

**Private, opt-in real-network verification.** This is a five-origin browser compatibility sample, not a new nationwide WAP survival census or evidence of physical-phone/WSP/WDP support. Historical R8 research is separately frozen in [FINAL_FINDINGS_20261029.md](FINAL_FINDINGS_20261029.md).

## Methods

- Five previously confirmed public, anonymous, historic WAP hosts; Nokia 7110 HTTP profile. Strict public DNS pinning, no redirects, no cookie submission, no proxy, no form submission or download execution.
- Actual **Agent** `open_page` and `follow_link` APIs, with verified R6 evidence and frozen R5 markup parser, used for initial four dual-page sites.
- Blue G specifically verified using the new opt-in `follow_do` path, selected by its actual per-card `do_links[]` result, **not a fabricated URL**. Only one additional public GET is sent.
- Only non-sensitive summary metrics and raw-body SHA-256 were emitted into Actions logs; no raw page or response header artifacts were published. Home/child snapshot may change at any time.

## Results

| Origin | Home (HTTP 200) | Actual same-origin second WML page (HTTP 200) | Relevant notes |
| --- | --- | --- | --- |
| `http://wap.shufaji.com/` | 1 card, 7 links, 95 chars; SHA `b1b361dec0ec0f44c720ef958f2c669a30c4902b8dcfbbd9fc52749f91af2156` | `/0x541B.wml`: 1 card, 3 links, 498 chars; SHA `0933ff65f3711000cebf8921a56b09d27252ed93b82b88c165f5898b8b8d3583` | Calligraphy dictionary text |
| `http://wap.517ming.com/` | 1 card, 13 links, 150 chars; SHA `0c59deaff29ba44fe64ae8ee4c792c4769e53a8fbbfbc4c553b65b68d694b293` | `/helian-xing.wml`: 1 card, 3 links, 96 chars; SHA `c6c23fcae7c9fb26a5c30ffcbcaab68f62cbee84391f8ff381899c6b799048fd` | Names directory; no forms executed |
| `http://wap.ee1234.com/` | 1 card, 29 links, 202 chars; SHA `1d6c466870f26552e7f82496bb37eedd2aee64539841e1b085b1a7befc52c8c3` | `/dongzuo-p1.wml`: 1 card, 9 links, 81 chars; SHA `2b22c5abfd18e5612fc6a564770f875ff8a551636e5924ef874a2151f753afae` | Listing only, no game binaries downloaded |
| `http://wap.uc123.com/` | 1 card, 40 links, 500 chars; SHA `93261ba17104a3f46faa9cc1a1a4b891add97301ca930cd77d789ac5e1271f99` | `/s_3457/`: 1 card, 0 links, 18 chars; SHA `519ce2e7a7532c42e7653d146c438411091dccaeafd6e029a069b049475cb530` | Same-origin WML **intermediary**, no claim outside redirect works |
| `http://wap.yuyangzhou.name/` | 1 card, **5 explicit do/go candidates**, 11 chars; SHA `97deed8c5332a314e8cb163ce61ff5a6576358427c015f6180f4e8a8bd227a6a` | `/m_service/default.wml`: 1 card, 42 chars; SHA `93342fd63493503b096a470671a7e8bd6f4fc7ddee3961136083c5022335c11d` | GB2312, `<do><go>` navigation; WMLScript not executed |

Original sanitized runs: [five-home baseline #40878683922](https://github.com/Blueteemo/wap-probe/actions/runs/40878683922), [Blue G structural diagnosis #40878887222](https://github.com/Blueteemo/wap-probe/actions/runs/40878887222), [explicit Blue G double-page acceptance #40879767921](https://github.com/Blueteemo/wap-probe/actions/runs/40879767921).

## Diagnosed compatibility issue and fix

Blue G's home has 5 `<do><go>` navigation actions and only 1 ordinary `<a>` tag. The previous Agent exposed only ordinary `<a>` links and intentionally excluded all `<go>` because a GET can have server-side effects. It therefore could parse the GB2312 homepage but could not reach `/m_service/default.wml` through the Agent API. **This was a navigation-classification gap, not a charset failure.**

Version 0.7.0 extracts a narrow subset of **no-input** `<do><go>` candidates from the exact parsed WML/WMLC source while preserving the frozen R5 binary decoder. Candidates remain separate from ordinary `links[]`, under `do_links[]`, and the existing `follow` path does not execute them. The new explicit `go` CLI / `wap_go` MCP tool requires a per-call `--execute` / `execute: true` plus the MCP server's `--allow-network` gate.

Eligibility is conservative: recognized `do` types, literal no-query/no-fragment href, GET only, no `postfield` or scripts or stateful variables, no input/select controls in the card. The shared navigation policy rejects cross-origin, authentication and obvious mutation URLs as well as WMLScript/binary download extensions. No `go` action is treated as an ordinary link or as a form submission. **This is not proof all GET endpoints are side-effect-free**; users must only opt in for public, harmless read-only destinations.

## Important limits

- These ten verified HTTP 200 responses all had `text/vnd.wap.wml` MIME. **No live WMLC response was captured during this five-origin sample.** WMLC decoding is still validated separately by pinned R5 binary fixtures, not by this live result.
- No live WSP/WDP, vintage Nokia phone or DSi/WAPDS validation. No cross-origin browsing, credential flow, form submission, game download, WMLScript execution or auto-redirect was attempted.
- All five were already known WML sources from prior historical R8 research; this is a **reader compatibility** test, not evidence of new discovery or an estimate of national WAP prevalence.
- The one-shot Actions workflow was removed after validation. Normal CI remains offline-only; the original opt-in manual origin workflow remains available.
