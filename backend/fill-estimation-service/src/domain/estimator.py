# backend/fill-estimation-service/src/domain/estimator.py
# -------------------------------------------------------------------------
# Core stateful algorithm to estimate the realistic fill percentage of a bin
# -------------------------------------------------------------------------

from .models import BinConfig, BinFillState


def estimate_fill(
    state: BinFillState,
    config: BinConfig,
    raw_distance_cm: float,
) -> tuple[BinFillState, float, bool]:
    """Updates the bin state and calculates the confirmed fill percentage.

    Args:
        state: Persistent state of the bin.
        config: Physical dimensions and parameters of the bin.
        raw_distance_cm: Sensor distance reading for the current cycle.

    Returns:
        tuple: (updated_state, fill_percent, is_emptied_this_cycle)
    """
    ratio_of_depth = raw_distance_cm / config.bin_depth_cm

    # 1. Check for genuine Empty/Pickup event
    if ratio_of_depth >= config.empty_ratio_threshold:
        state.near_empty_streak += 1
    else:
        state.near_empty_streak = 0

    if state.near_empty_streak >= config.empty_confirm_cycles:
        # Bin has been verified emptied -- reset to default baseline
        state = BinFillState(
            confirmed_distance_cm=raw_distance_cm,
            candidate_distance_cm=None,
            candidate_streak=0,
            near_empty_streak=0,
        )
        return state, 0.0, True

    # 2. Check and accumulate candidate for filling
    if (
        state.candidate_distance_cm is None
        or abs(raw_distance_cm - state.candidate_distance_cm) > config.tolerance_cm
    ):
        state.candidate_distance_cm = raw_distance_cm
        state.candidate_streak = 1
    else:
        state.candidate_streak += 1
        state.candidate_distance_cm = (
            state.candidate_distance_cm + raw_distance_cm
        ) / 2.0

    # Confirm the candidate if it has repeated consistently
    is_confirmed = state.candidate_streak >= config.confirm_cycles

    if is_confirmed:
        # Ratchet mechanism: Trash does not remove itself. Only allow distance to decrease
        # (which represents fill-level increase), unless an empty-event was triggered above.
        state.confirmed_distance_cm = min(
            state.confirmed_distance_cm, state.candidate_distance_cm
        )

    # 3. Calculate finalized percentage
    usable_depth = config.usable_depth_cm
    filled_depth = config.bin_depth_cm - state.confirmed_distance_cm

    percent = (filled_depth / usable_depth) * 100.0
    percent = max(0.0, min(100.0, percent))  # Clamping between 0% and 100%

    return state, round(percent, 1), False
