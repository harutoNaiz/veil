MODEL: claude-sonnet-5-5
DONE. Verify: veil/tools/verify/D-oov-words.ps1 -> PASS (ktlint, kit check, :teacher:test + Siglip2TokenizerTest golden, :app:compileDebugKotlin).
- New app wire/ml/OovTextEncoder.kt: Siglip2Tokenizer (GemmaBpe, pad/truncate 64, EOS kept) and LazyTextEncoder (opens siglip2-text.onnx from ModelStore dir only on first encode; close() releases it, so nothing loads at startup).
- AutoCal.compileAuto already uses vocab.bin for in-vocab words and ensemble (5 templates, l2-mean-l2) for OOV; TeacherDebugActivity now passes LazyTextEncoder (was a null TOKENIZER stub).
- kit.ps1 model list: added siglip2-text.onnx (siglip2-tok.bin already there).
- Tests: app Siglip2TokenizerTest + resources/tok/golden-oov.json (HF tokenizer, 3 words x 5 templates, 64-padded); teacher AutoCalOovTest (fake encoder, ensemble + unit norm).
- Real 1.1 GB model never loaded on the laptop; on-device OOV run not exercised (needs phone).
- Stale class doc in TeacherDebugActivity still says tokenizer deferred.

## Independent verification (orchestrator)
- 11:41: `tools/verify/D-oov-words.ps1` re-run → VERIFY D-oov-words: PASS (evidence/D-oov-words-verify.txt). Commit 30d60ff.
