from scripts.benchmark_glance import benchmark


def test_warm_glance_view_p95_is_below_300ms() -> None:
    result = benchmark(warmup=10, iterations=50)

    assert result["p95_ms"] <= 300, result

