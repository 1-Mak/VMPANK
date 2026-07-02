from vpnctl import monitoring


def test_parse_checkhost_results_mixed():
    data = {
        "ru1.node.check-host.net": [{"time": 0.123, "address": "1.2.3.4"}],
        "ru2.node.check-host.net": [{"error": "Timeout"}],
        "ru3.node.check-host.net": None,  # ещё в ожидании
    }
    results = {r.node: r for r in monitoring.parse_checkhost_results(data)}
    assert results["ru1.node.check-host.net"].ok
    assert results["ru1.node.check-host.net"].time_ms == 123.0
    assert not results["ru2.node.check-host.net"].ok
    assert results["ru2.node.check-host.net"].error == "Timeout"
    assert not results["ru3.node.check-host.net"].ok


def test_availability_report_reachability():
    report = monitoring.AvailabilityReport(
        ip="1.2.3.4",
        port=443,
        nodes=[
            monitoring.NodeResult("ru1", ok=False, time_ms=None, error="x"),
            monitoring.NodeResult("ru2", ok=True, time_ms=10.0),
        ],
    )
    assert report.reachable_from_ru
    assert "1/2" in report.summary


def test_health_report_aggregates():
    report = monitoring.HealthReport()
    report.add("a", True)
    report.add("b", False, "disk full")
    assert not report.healthy
    assert report.details["b"] == "disk full"
