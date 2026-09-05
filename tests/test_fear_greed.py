import pytest

from trader_sentiment.fear_greed import BANDS, classify, load_or_fetch, to_frame


@pytest.mark.parametrize("value,band", [
    (0, "Extreme Fear"), (24, "Extreme Fear"), (25, "Fear"), (44, "Fear"),
    (45, "Neutral"), (54, "Neutral"), (55, "Greed"), (74, "Greed"),
    (75, "Extreme Greed"), (100, "Extreme Greed"),
])
def test_every_band_boundary(value, band):
    assert classify(value) == band


@pytest.mark.parametrize("value", [-1, 101, 1000])
def test_an_impossible_index_value_is_rejected(value):
    with pytest.raises(ValueError):
        classify(value)


def test_bands_are_ordered_and_cover_the_range():
    ceilings = [c for c, _ in BANDS]
    assert ceilings == sorted(ceilings)
    assert ceilings[-1] < 100


def test_payload_becomes_the_four_columns_the_analysis_expects():
    payload = {"data": [
        {"timestamp": "1733097600", "value": "20", "value_classification": "Extreme Fear"},
        {"timestamp": "1733184000", "value": "80", "value_classification": "Extreme Greed"},
    ]}
    frame = to_frame(payload)
    assert list(frame.columns) == ["timestamp", "value", "classification", "date"]
    assert frame["value"].tolist() == [20, 80]
    assert str(frame["date"].iloc[0]) == "2024-12-02"


def test_an_empty_payload_fails_loudly_rather_than_yielding_no_rows():
    with pytest.raises(ValueError, match="no data"):
        to_frame({"data": []})


def test_snapshot_is_read_from_disk_without_touching_the_network(tmp_path, fear_greed_frame):
    path = tmp_path / "fng.csv"
    fear_greed_frame.to_csv(path, index=False)

    def explode(*_a, **_k):
        raise AssertionError("load_or_fetch hit the network despite a local snapshot")

    import trader_sentiment.fear_greed as fg
    original, fg._fetch = fg._fetch, explode
    try:
        out = load_or_fetch(path)
    finally:
        fg._fetch = original
    assert len(out) == 2
    assert str(out["date"].iloc[0]) == "2024-12-02"
