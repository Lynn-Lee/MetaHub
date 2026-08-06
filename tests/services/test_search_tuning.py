from app.services.search_tuning import (
    ThresholdMeasurement,
    build_representative_fixture,
    build_v01_query_cases,
    calculate_recall,
    percentile_95,
    recommend_threshold,
)


def test_v01_query_cases_cover_required_query_mix() -> None:
    cases = build_v01_query_cases()

    assert 30 <= len(cases) <= 50
    assert {"zh_2", "zh_4", "english", "mixed"}.issubset({case.category for case in cases})
    assert all(case.expected_urns for case in cases)


def test_representative_fixture_contains_all_expected_query_targets() -> None:
    fixture = build_representative_fixture()
    expected_urns = {urn for case in build_v01_query_cases() for urn in case.expected_urns}
    column_urns = {column["urn"] for column in fixture.columns}
    table_urns = {table["urn"] for table in fixture.tables}

    assert expected_urns.issubset(column_urns)
    assert {column["table_urn"] for column in fixture.columns}.issubset(table_urns)


def test_search_tuning_metrics_calculate_recall_and_p95() -> None:
    assert calculate_recall(["urn:a", "urn:b"], ["urn:b", "urn:c"]) == 0.5
    assert percentile_95([1.0, 2.0, 3.0, 100.0]) == 100.0


def test_recommend_threshold_prefers_highest_threshold_under_recall_and_latency_budget() -> None:
    measurements = [
        ThresholdMeasurement(threshold=0.05, recall=1.0, p95_ms=80.0, avg_result_count=25.0),
        ThresholdMeasurement(threshold=0.10, recall=1.0, p95_ms=45.0, avg_result_count=12.0),
        ThresholdMeasurement(threshold=0.15, recall=0.82, p95_ms=30.0, avg_result_count=6.0),
        ThresholdMeasurement(threshold=0.20, recall=0.70, p95_ms=20.0, avg_result_count=3.0),
    ]

    assert recommend_threshold(measurements, min_recall=0.9, max_p95_ms=500).threshold == 0.10
