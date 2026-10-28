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
