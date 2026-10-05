# Phase 3.1 Export the models · BUILT (proof test PASS)
Commits: see 3.1.1-3.1.3 records (incl. 71d67c9) · Proof test PT-3.1 "Same answers, new engine": PASS (2026-10-06, evidence/H4-pt-3.1.txt)

## Proof test results (machine part)
- **Agreement:** torch and ONNX give the same decisions 99.17% of the time on cats and spiders (threshold ≥ 98%) → PASS.
- **Concept lists:** bicycles, dogs+flowers and cats+spiders all run on ONNX, and the .onnx files are unchanged afterwards. Concepts never need a re-export.
- **Static shapes and opset 17** for every export:
  - NudeNet 320n and 640m;
  - SigLIP2 image b1, b4 and b16, plus the SigLIP2 text model;
  - toxicity seq128 and seq256;
  - YOLOE-26s embed-top100.

## Deviations
- The YOLOE text encoder export is not used. Variant C uses SigLIP2 text instead (accepted earlier).
