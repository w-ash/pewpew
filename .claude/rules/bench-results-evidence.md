---
paths:
  - "bench/results/**"
---

# Frozen evidence

`bench/results/` is committed study evidence. Never rewrite an existing
results file — post-hoc findings are appended as dated addenda (precedent:
the 2026-07-16 authoring report). Re-running a bench script rewrites its
JSON artifact (at minimum the `git_sha` stamp); after any incidental rerun,
`git checkout` the artifact unless the regeneration was the point.
