from tvt.media.screenshots import _screenshot_times


def test_quarter_points_of_a_long_video():
    assert _screenshot_times(1070) == [267.5, 535.0, 802.5]


def test_quarter_points_of_a_short_video():
    assert _screenshot_times(8) == [2.0, 4.0, 6.0]


def test_times_are_in_order():
    assert _screenshot_times(100) == [25.0, 50.0, 75.0]


def test_never_returns_out_of_range_times():
    for duration in (0.5, 1, 5, 20, 60, 3600):
        for at in _screenshot_times(duration):
            assert 0 < at < duration
