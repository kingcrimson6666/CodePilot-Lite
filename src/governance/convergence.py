from __future__ import annotations


def reached_stability(recent_success_rates: list[float], threshold: float = 0.65) -> bool:
    if len(recent_success_rates) < 2:
        return False
    return all(rate >= threshold for rate in recent_success_rates[-2:])


def evaluate_release_gate(
    recent_success_rates: list[float],
    threshold: float = 0.65,
    min_runs: int = 2,
    max_drop: float = 0.05,
) -> dict:
    rates = [float(x) for x in recent_success_rates]
    if len(rates) < min_runs:
        return {
            "allowed": False,
            "reason": "not_enough_runs",
            "required_runs": min_runs,
            "observed_runs": len(rates),
        }

    window = rates[-min_runs:]
    stable = all(rate >= threshold for rate in window)
    latest = window[-1]
    previous = window[-2] if len(window) >= 2 else window[-1]
    degraded = (previous - latest) > max_drop

    if not stable:
        return {
            "allowed": False,
            "reason": "below_threshold",
            "window": window,
            "threshold": threshold,
        }

    if degraded:
        return {
            "allowed": False,
            "reason": "degraded",
            "window": window,
            "max_drop": max_drop,
        }

    return {
        "allowed": True,
        "reason": "stable",
        "window": window,
        "threshold": threshold,
        "max_drop": max_drop,
    }
