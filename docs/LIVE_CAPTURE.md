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
