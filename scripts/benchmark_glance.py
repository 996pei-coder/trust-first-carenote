"""Measure the in-process warm-path Top Card latency used in the brief."""

import argparse
import tempfile
import time
from pathlib import Path
from typing import Dict, List

from fastapi.testclient import TestClient

from app.main import create_app


def percentile(samples: List[float], percentile_value: float) -> float:
    ordered = sorted(samples)
    index = min(round((len(ordered) - 1) * percentile_value), len(ordered) - 1)
    return ordered[index]


def benchmark(warmup: int = 20, iterations: int = 200) -> Dict[str, float]:
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(f"sqlite:///{Path(directory) / 'benchmark.db'}")
        with TestClient(app) as client:
            for _ in range(warmup):
                response = client.get(
                    "/api/patients/1/top-card", headers={"X-User-ID": "3"}
                )
                response.raise_for_status()
            samples = []
            for _ in range(iterations):
                started = time.perf_counter()
                response = client.get(
                    "/api/patients/1/top-card", headers={"X-User-ID": "3"}
                )
                response.raise_for_status()
                samples.append((time.perf_counter() - started) * 1000)
    return {
        "p50_ms": percentile(samples, 0.50),
        "p95_ms": percentile(samples, 0.95),
        "p99_ms": percentile(samples, 0.99),
        "max_ms": max(samples),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=200)
    args = parser.parse_args()
    result = benchmark(args.warmup, args.iterations)
    print(f"warmup={args.warmup} iterations={args.iterations}")
    print(" ".join(f"{key}={value:.2f}" for key, value in result.items()))


if __name__ == "__main__":
    main()

