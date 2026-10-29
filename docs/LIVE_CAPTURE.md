# R6 direct-origin WAP capture

**Initial mission:** find live Chinese-origin WML/WMLC services, capture complete origin HTTP evidence and establish a reachable second GET; separately compare native WAP / WAP Labs if available. The 8 historical endpoints are only candidates.

## Explicit opt-in

```sh
PYTHONPATH=src python3 -m wap_probe.pipeline --matrix
PYTHONPATH=src python3 -m wap_probe.pipeline --matrix --limit 2 --execute \
  --out evidence/first-two
```

Requires curl, a direct public network, and the frozen R5 archive unpacked to `.r5_unpacked/wap-probe-live-discovery-r5/probe`. Choose an unused `--out` directory; existing roots are never overwritten. Set `--delay` to >=1 second (default: 2). Individual HTTP/HTTPS and Nokia/S60 attempts remain separate.

The collector rejects non-public DNS answers and IP literals, pins one public DNS address via `curl --resolve`, disables proxies and curl config, does not follow redirects or send cookies/auth/POST, and uses verified TLS and a 1MiB response body cap. Curl stores response headers and the transferred entity body, not raw TCP bytes. Evidence folders contain `metadata.json`, `headers.bin`, `body.bin`, `stderr.txt`, `curl_writeout.txt`, plus `r5_export.json` where parsing succeeded.

The pipeline runs **real frozen R5** on exactly captured body bytes, can traverse ordinary `#card` links without network, chooses a safe same-origin public GET in a reachable card, and captures/parses one second page. It never labels an origin or navigation A-grade automatically. Do not treat `TWO_PAGE_EVIDENCE_MATCHED` as independent WAP Labs/WSP/WDP proof or actual physical Nokia validation.

**CI is offline only.** Operator must check authorization and restrict targets to public no-login pages. Raw captures are ignored by git.

## Explicit second-page selection from real WML links

Observed in GitHub Actions run #40677385820 (2026-10-28, https://tx.com.cn/, wap1):
the frozen R5 export contained these verified homepage GET links:

- Index 8, 分类: /zone/cs/category.do
- Index 9, 服务: /editor/cs/official.do
- Index 16, 小说: /read/cs/goodBook.do

These links were present in the original WML deck, but their second-page
availability is NOT yet confirmed. The manual workflow now has public_section
options: auto, tx_categories, tx_services, tx_novels. Use tx_categories first
with site=tx.com.cn, scheme=https, profile=wap1.

The chosen literal path is matched against the actual R5 export from the NEW
homepage capture. Server-provided dynamic query values are preserved. If no
matching same-origin GET exists, no second request is made. No guessed child
URL, cookie, redirect, login, or POST is introduced.

Local equivalent (only where direct public network access is permitted):

    PYTHONPATH=src python3 -m wap_probe.pipeline --url https://tx.com.cn/ \
      --profile wap1 --prefer-path /zone/cs/category.do \
      --out evidence/tx-category-001 --execute

An Actions run completing successfully is not an A-navigation PASS.

## Anonymous JSESSIONID continuity: controlled two-GET experiment

Evidence in three real HTTPS captures from 2026-10-28 shows that the home
WML page contains stable channel z values 900000010 through 900000019, while
each home response sets a new JSESSIONID. Independent anonymous requests to
/love/index.do and /zone/cs/category.do returned HTTP 302 pointing to
http://tx.com.cn/in/guest.do?returl=..., without a Cookie header.

The optional manual workflow input anonymous_session=jsessionid_https_only
is restricted to tx.com.cn, HTTPS, the tx_categories link, and the Nokia
profile selected for the comparison. The default is none.

The experiment first GETs the fresh WML homepage without cookies, validates
the WML through R5, then extracts exactly one 32-hex, host-only JSESSIONID.
The second GET is the actual homepage-linked /zone/cs/category.do URL with
its freshly parsed query. Only the new anonymous JSESSIONID is replayed to
the same HTTPS tx.com.cn host. No browser, authentication, cfrom, csstype,
access or txEncodeUid cookies are imported. No redirects are followed and
no HTTP downgrade or /in/guest.do is visited.

The cookie is written to a temporary 0600 Netscape-format curl cookie file
and removed after the request. Session values are never written to run
reports or curl command arguments, but the private raw headers can include
Set-Cookie; treat all raw evidence as sensitive. The artifact expires in 3
days. No more than two independent GET requests can be issued per run.

Use the manual workflow with site=tx.com.cn, scheme=https, profile=wap1,
public_section=tx_categories, anonymous_session=jsessionid_https_only.
The no-cookie baseline was run #40693454540. This is not a simultaneous
A/B experiment: if the new second-page request returns 302 again, it only
indicates that JSESSIONID alone was not sufficient on this attempt.

Equivalent explicit local invocation:

    PYTHONPATH=src python3 -m wap_probe.pipeline --url https://tx.com.cn/ \
      --profile wap1 --prefer-path /zone/cs/category.do \
      --anonymous-jsessionid --out evidence/tx-category-cookie01 --execute

## Failed live session attempt: 2026-10-28

Actions run #40695465360 fetched and parsed the HTTPS WML home, and selected
/zone/cs/category.do. It **never sent the second GET**: the CLI pacing
wrapper omitted the optional session_cookie keyword argument, raising
TypeError before reaching curl. This run is an execution failure, NOT evidence
that anonymous session continuity failed. The CLI wrapper now forwards the
optional session cookie, and a full CLI-level mock regression verifies exactly
two requests, preserved pacing, and non-disclosure in the run report.

## Automated no-click anonymous session recheck: 2026-10-29

GitHub Actions run [#40845259067](https://github.com/Blueteemo/wap-probe/actions/runs/40845259067),
triggered by a temporary path-scoped push workflow, completed its bounded
two-GET experiment without requiring a manual Actions click. The temporary
workflow was removed after this run; the frozen R5 ZIP and pipeline are unchanged.

- Home: `https://tx.com.cn/`, Nokia 7110 profile, direct HTTPS GET,
  HTTP **200**, `text/vnd.wap.wml;charset=UTF-8`, **6,960 entity-body bytes**,
  SHA-256 `b5ec8ba4132f2025df9bbb34dcaf736d961630ce52c88d9f8be3ff6076a44611`.
- Frozen R5 parsed the home successfully: **one WML card and 40 parsed links**.
  The actual homepage link at index 8 led to the public-category path
  `/zone/cs/category.do` (channel query values are server-provided).
- The one subsequent HTTPS GET used **only the fresh anonymous host-local
  JSESSIONID** captured from that homepage; no login, POST or redirect following.
  It received **HTTP 302**, pointing to the HTTP guest-entry flow
  `/in/guest.do`. The runner did not follow the redirect or downgrade to HTTP.
- Machine result: `CHILD_NOT_WML_EVIDENCE`,
  `home_capture=WML_CAPTURED_NEEDS_R5`,
  `child_capture=REDIRECT`. Both formal A gates remain **PENDING**:
  this supports a live WML homepage but not a successfully fetched WML child.
- Private raw evidence: artifact `tx-anon-one-shot-20261029`, artifact ID
  `12884179095`, 3-day retention. **It includes raw Set-Cookie headers**;
  do not publish or copy the raw artifact into Git history. The SHA and summary
  in this section are safe non-secret audit pointers.

**Implication:** anonymous JSESSIONID alone did not bypass the site's
visitor-entry redirect on this attempt. Future checks should prefer genuinely
public same-origin child links or identify the documented guest navigation
flow without using login credentials; avoid repeating the same category GET
in a loop or treating the 302 as a domain-wide failure.

## R6 new domestic two-page WML evidence — 2026-10-29

Two **Chinese-language historic WAP origin hosts** now have captured,
distinct, navigable WML home/child pages with no authentication or redirect.
This is real progress beyond the earlier strong tx.com.cn home-only candidate.
Do not conflate two domains with two independent maintainers: their footers
cross-link, so common ownership/hosting remains possible.

| Profile + URL | HTTP origin result | Child selected from fresh R5 homepage | Child result |
| --- | --- | --- | --- |
| Nokia 7110, http://wap.shufaji.com/ | 200; `text/vnd.wap.wml`; 1543 B; SHA-256 `494f2c10e76e0ad8627553ca857a623604d416fd1a192fda51c63ef103dcf6da` | `/0x541B.wml` (the character 君) | 200; WML; 4648 B; SHA-256 `f2847963831362437a726d7d08a12dec5bad2b9800c96892f307388a13c1480a` |
| Symbian S60v3, http://wap.shufaji.com/ | 200; WML; 1543 B; SHA-256 `92dce101db1176c35633dc82a88f38db9665a7debd7831ceabbafa97711e446d` | `/0x541B.wml` | 200; WML; 4648 B; SHA-256 `f890118195b07957f9c39bca5101840126133e09833f92ad3750e8fee014b125` |
| Nokia 7110, http://wap.517ming.com/ | 200; WML; 2442 B; SHA-256 `d791f81069570aaac5acb5fd72724910ed9781184d4a73c7aea0c1dda94551b3` | `/helian-xing.wml` (赫连 surname) | 200; WML; 1201 B; SHA-256 `9bc174b9f5c207376a887935a860b1a72617bc6b2284fbd9c58f8789ce045958` |

Each captured document contains one distinct `<card>`, and each was
parsed by frozen R5 (`status=ok`) and independently well-formed under
Python `xml.etree.ElementTree`. Home title/content and child title/content
differ semantically (calligraphy dictionary entries versus the name
directory), ruling out a merely repeated homepage. Both home pages displayed
a server clock that changed from 17:02 to 17:04 China local time across
independent runs, indicating some active page generation; this does not
establish that editorial content is regularly maintained.

**Network boundaries:** a separate `https://wap.shufaji.com/` attempt
timed out (curl exit 28 after ~8 s); HTTP works, HTTPS not proven.
The IP138 exact historic `http://qq.ip138.com/train/search_train.wml`
returned 301 to the equivalent HTTPS URL; that URL returned HTTP 302 to
`https://dnsdblookup.com/`, so the exact former WML endpoint is not
currently verified. Do not generalize these path-specific results to
entire domains.

**tx.com.cn visitor mechanism:** independently parsed homepage WML in
both new attempts. The homepage-linked `/editor/cs/official.do` returned
HTTP 302 to `http://tx.com.cn/in/guest.do?returl=...` (not followed).
The homepage-linked `/read/cs/goodBook.do` returned HTTP 502 (nginx,
HTML). Earlier anonymous-JSESSIONID replay to `/zone/cs/category.do`
also got 302. These outcomes do not show whether registration is necessary:
the guest flow has not been completed. No credentials, login, POST, or
automatic protocol downgrade were used.

**Artifacts:** [run 40846429748](https://github.com/Blueteemo/wap-probe/actions/runs/40846429748)
(artifact ID 12885087285), [run 40846746719](https://github.com/Blueteemo/wap-probe/actions/runs/40846746719)
(artifact ID 12884693376). Private raw headers may contain Set-Cookie
values; never publish or commit them. Both artifacts retain for 3 days.

**Grade policy:** `TWO_PAGE_EVIDENCE_MATCHED` is concrete R5-backed
two-page evidence, but the pre-existing `A_origin` and `A_navigation`
fields stay `PENDING` until the separate WAP Labs parser/transport
cross-check and final human review. Physical Nokia browser/transport is
also untested. Next priority is cross-validate one shufaji and one
517ming capture using a fixed WAP Labs revision, then finalize R7 and
document HTTP-only feasibility without stretching the investigation.

## R7 independent WaveNav engine cross-check — 2026-10-29

This is a **true second parser/rendering implementation**, not another
test using frozen R5. In
[GitHub Actions run #40847596595](https://github.com/Blueteemo/wap-probe/actions/runs/40847596595),
the runner checked out public `dills122/wap-labs` at immutable Git SHA
`9cd7ab97dc6752fc1616feb3505a58603f6a45df`, compiled its native
`wavenav_engine` v0.3.0 with default WASM bindings disabled, and called
`WmlEngine::load_deck_context`, `active_card_id`, and `render_frame`
on **unchanged** six real source `body.bin` files.

No live target website requests were sent in R7. R6 originals were downloaded
from **private** Actions artifacts #12885087285 (run 40846429748) and
#12884693376 (run 40846746719), whose filenames and expected SHA-256
values are fixed in the R7 job log. Every input hash was reverified, so
this is not a synthetic fixture substitution.

| Unchanged WML capture | Native WaveNav load | Card ID | Rendered frame rows | Content rows |
| --- | --- | --- | ---: | ---: |
| shufaji Nokia, home | PASS | 6 chars | 14 | 32 |
| shufaji Nokia, child `/0x541B.wml` | PASS | 6 chars | 9 | 195 |
| shufaji S60, home | PASS | 6 chars | 14 | 32 |
| shufaji S60, child `/0x541B.wml` | PASS | 6 chars | 9 | 195 |
| 517ming Nokia, home | PASS | 6 chars | 14 | 52 |
| 517ming Nokia, child `/helian-xing.wml` | PASS | 6 chars | 11 | 30 |

**Result: 6/6 byte hashes + 6/6 independent WaveNav WML load/render PASS.**
This strongly upgrades the two-domain, two-page **HTTP WML evidence**.
The WML home→child href relationship and real HTTP GETs were independently
recorded in R6. The R7 engine replay loaded each page independently; it
did **not** synthesize a handset keypress or issue a WAP network navigation.

**Limits, explicitly not tested:**
- The pinned WaveNav implementation is pre-alpha/pre-conformance; it is
  independent and valuable evidence, not a WML 1.1 DTD or full Class C
  conformance certificate.
- No original Nokia/S60 hardware browser was tested.
- No native WSP/WDP or authenticated carrier WAP gateway was tested.
- R7 did not re-run a separate Lowband HTTP transport session against the
  live origins (it checked historical direct-origin curl capture bytes).
- HTTP responses are confirmed for the two domains; HTTPS and old TLS
  compatibility are not inferred from this HTTP-only evidence.
- The original `A_origin` and `A_navigation` automation fields stay
  `PENDING`, rather than being silently rewritten as PASS.

**Research judgment:** classify `wap.shufaji.com` and
`wap.517ming.com` as **confirmed live Chinese HTTP WML two-page samples,
cross-validated by two parser implementations**; track physical-device/
WSP compatibility separately as `UNTESTED`. A public claim that a 2000s
Nokia can browse either site without a suitable WAP gateway would be
unsubstantiated.

**Operational cleanup:** the temporary R7 workflow and the older 2026-10-29
one-shot public survey workflow have been retired, leaving only the stable
offline test and explicit manual sample workflows. R5 archive and production
pipeline are unchanged. Sanitized R7 engine results artifact
`r7-wavenav-results-40847596595` (artifact ID 12884534955) is retained
for 7 days; the persistent CI log and this report preserve the outcome.

## R8 completion and final index — 2026-10-29

All eight priority domestic historical candidate origins now have at least one
bounded direct-origin HTTP sampling result. Five serve original WML home and
actual WML child pages: shufaji, 517ming, ee1234, uc123 and Blue G Lab.
TX and CCTV have WML home-only evidence; CCTV's content is dated 2006.
The exact historical IP138 train WML URL redirects to a different service.
UC123 child is a redirect card, not usable external news content.

Independent WaveNav replay at pinned `9cd7ab97`: prior R7 6/6; newly
captured R8 sample 7/7; Blue G Lab GB2312 origin bytes strictly decoded to
Unicode after SHA-256 comparison, then 3/3 load and render success. No new
external WAP site GET was required for those independent replays.

The authoritative concise survey closure, status table, source hashes,
run links and legacy handset limitations are now at
[FINAL_FINDINGS_20261029.md](FINAL_FINDINGS_20261029.md). All temporary R8
workflows are retired. Source archive and production pipeline are unchanged.
