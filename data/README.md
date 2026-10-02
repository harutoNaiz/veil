# data/ is private

Everything in this folder except this file is git-ignored (see `.gitignore`).
It holds screenshots, recordings, labels and evidence from real phones and test accounts.
It is never pushed to a public remote and never uploaded anywhere, except Qualcomm AI Hub jobs that a phase spec lists explicitly.
Planned subfolders: `screens/` (Phase 1.2), `labels/` (Phase 1.2), `recordings/` (Phase 2.1) and `evidence/<phase>/` (large evidence such as videos and traces).
Check that a file is ignored with `git check-ignore -v data/x.png`.
