MODEL: claude-sonnet-5-5
D-72-fetch: coco._get follows redirects + https w/ ALPN http/1.1 (Flickr 429 on default TLS); fetch_one uses https, backoff; phase_embed errors on no images. verify PASS

## Independent verification (orchestrator)
- 02:22: `tools/verify/D-72-fetch.ps1` re-run → VERIFY D-72-fetch: PASS (evidence/D-72-fetch-verify.txt). Commit 9ffcd89.
