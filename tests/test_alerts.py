from worker.worker import update_state


def test_single_failure_does_not_alert():
    state = {}
    assert update_state(state, 1, False) is None


def test_two_failures_in_a_row_alert_once():
    state = {}
    update_state(state, 1, False)
    assert update_state(state, 1, False) == "down"
    assert update_state(state, 1, False) is None   # no repeat alert


def test_recovery_alerts_once():
    state = {}
    update_state(state, 1, False)
    update_state(state, 1, False)
    assert update_state(state, 1, True) == "recovered"
    assert update_state(state, 1, True) is None


def test_blip_resets_the_counter():
    state = {}
    update_state(state, 1, False)
    update_state(state, 1, True)
    assert update_state(state, 1, False) is None   # counter restarted