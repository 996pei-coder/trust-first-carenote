# Glance View Performance

## Result

Measured on 2026-08-26 on the local candidate machine (`Darwin arm64`, Python 3.9.6):

| Metric | Warm-path latency |
|---|---:|
| P50 | 1.83 ms |
| P95 | 2.09 ms |
| P99 | 2.28 ms |
| Maximum | 12.21 ms |

The measured P95 is below the required 300 ms threshold.

## Method

`scripts/benchmark_glance.py` creates a temporary SQLite database, starts the FastAPI application in-process, performs 20 warm-up requests, and measures 300 authenticated requests to `GET /api/patients/1/top-card` using `time.perf_counter()`.

Reproduce with:

```bash
python scripts/benchmark_glance.py --warmup 20 --iterations 300
```

The automated test uses 10 warm-ups and 50 measured requests and fails if P95 exceeds 300 ms.

## Interpretation and limitation

This is a warm-path application benchmark, not a production network benchmark. It includes FastAPI routing, server-side RBAC, SQLite queries, visibility filtering, importance calculation, and response serialization. It excludes TLS termination, network transit, browser rendering, concurrent production load, and managed-database latency. Those components must be load-tested in the target deployment before making a production SLO claim.

