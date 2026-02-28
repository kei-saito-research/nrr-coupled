#!/usr/bin/env python3
"""Minimal reproducible simulator for uncoupled vs coupled updates.

This script provides a falsifiable harness for cp evaluation planning.
It uses synthetic dependency graphs and an oracle (operator, target) stream
shared by both systems so only client-side update rules differ.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass
class ScenarioConfig:
    name: str
    n: int
    turns: int
    alpha: float
    beta: float
    a_true: List[List[float]]
    a_model: List[List[float]]


def clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def normalize(v: List[float]) -> List[float]:
    s = sum(v)
    if s <= 0.0:
        return [1.0 / len(v)] * len(v)
    return [x / s for x in v]


def init_uniform(n: int) -> List[float]:
    return [1.0 / n] * n


def l1_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def uncoupled_update(w: List[float], op: str, k: int, alpha: float, eps: float, umax: float) -> List[float]:
    out = w[:]
    delta = alpha if op == "sigma" else -alpha
    out[k] = clip(out[k] + delta, eps, umax)
    return normalize(out)


def coupled_update(
    w: List[float],
    op: str,
    k: int,
    alpha: float,
    beta: float,
    a: List[List[float]],
    eps: float,
    umax: float,
) -> List[float]:
    out = w[:]
    delta = alpha if op == "sigma" else -alpha
    old_k = out[k]
    out[k] = clip(out[k] + delta, eps, umax)
    d = out[k] - old_k

    n = len(out)
    for i in range(n):
        if i == k:
            continue
        coeff = a[i][k]
        if coeff == 0.0:
            continue
        out[i] = clip(out[i] + beta * coeff * d, eps, umax)

    return normalize(out)


def step_truth(
    w_true: List[float], op: str, k: int, alpha: float, beta: float, a_true: List[List[float]], eps: float, umax: float
) -> List[float]:
    # The hidden process follows the same coupled form but with true dependencies.
    return coupled_update(w_true, op, k, alpha, beta, a_true, eps, umax)


def random_operator() -> str:
    return "sigma" if random.random() < 0.5 else "delta"


def run_once(cfg: ScenarioConfig, seed: int) -> Dict[str, float]:
    random.seed(seed)
    eps = 1e-6
    umax = 1.0 - eps

    w_true = init_uniform(cfg.n)
    w_base = init_uniform(cfg.n)
    w_cp = init_uniform(cfg.n)

    base_l1_sum = 0.0
    cp_l1_sum = 0.0
    base_corrections = 0
    cp_corrections = 0
    base_osc_pairs = 0
    cp_osc_pairs = 0

    base_prev_dist = l1_distance(w_base, w_true)
    cp_prev_dist = l1_distance(w_cp, w_true)
    base_prev_step = [0.0] * cfg.n
    cp_prev_step = [0.0] * cfg.n

    for _ in range(cfg.turns):
        k = random.randrange(cfg.n)
        op = random_operator()

        w_true = step_truth(w_true, op, k, cfg.alpha, cfg.beta, cfg.a_true, eps, umax)
        w_base_next = uncoupled_update(w_base, op, k, cfg.alpha, eps, umax)
        w_cp_next = coupled_update(w_cp, op, k, cfg.alpha, cfg.beta, cfg.a_model, eps, umax)

        base_dist = l1_distance(w_base_next, w_true)
        cp_dist = l1_distance(w_cp_next, w_true)

        base_l1_sum += base_dist
        cp_l1_sum += cp_dist

        if base_dist > base_prev_dist:
            base_corrections += 1
        if cp_dist > cp_prev_dist:
            cp_corrections += 1

        # Oscillation proxy: frequent direction reversal in candidate deltas.
        for i in range(cfg.n):
            b_step = w_base_next[i] - w_base[i]
            c_step = w_cp_next[i] - w_cp[i]
            if b_step * base_prev_step[i] < 0:
                base_osc_pairs += 1
            if c_step * cp_prev_step[i] < 0:
                cp_osc_pairs += 1
            base_prev_step[i] = b_step
            cp_prev_step[i] = c_step

        w_base = w_base_next
        w_cp = w_cp_next
        base_prev_dist = base_dist
        cp_prev_dist = cp_dist

    base_mean_l1 = base_l1_sum / cfg.turns
    cp_mean_l1 = cp_l1_sum / cfg.turns

    # Utility in [0,1]: lower tracking error is better.
    u_base = 1.0 - 0.5 * base_mean_l1
    u_cp = 1.0 - 0.5 * cp_mean_l1

    return {
        "u_base": u_base,
        "u_cp": u_cp,
        "u_diff_cp_minus_base": u_cp - u_base,
        "correction_rate_base": base_corrections / cfg.turns,
        "correction_rate_cp": cp_corrections / cfg.turns,
        "osc_rate_base": base_osc_pairs / max(1, cfg.turns * cfg.n),
        "osc_rate_cp": cp_osc_pairs / max(1, cfg.turns * cfg.n),
    }


def mean_dict(rows: List[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {}
    keys = rows[0].keys()
    return {k: sum(r[k] for r in rows) / len(rows) for k in keys}


def make_ring_dependency(n: int, w: float) -> List[List[float]]:
    a = [[0.0 for _ in range(n)] for _ in range(n)]
    for j in range(n):
        a[(j + 1) % n][j] = w
        a[(j - 1) % n][j] = -w / 2.0
    return a


def zero_dependency(n: int) -> List[List[float]]:
    return [[0.0 for _ in range(n)] for _ in range(n)]


def perturb_dependency(a: List[List[float]], p: float) -> List[List[float]]:
    n = len(a)
    out = [row[:] for row in a]
    for i in range(n):
        for j in range(n):
            if random.random() < p:
                out[i][j] = -out[i][j]
    return out


def build_scenarios(n: int, turns: int, alpha: float, beta: float) -> List[ScenarioConfig]:
    dep = make_ring_dependency(n, w=0.7)
    indep = zero_dependency(n)

    random.seed(2026)
    mismatch = perturb_dependency(dep, p=0.35)

    return [
        ScenarioConfig("D-dependent", n, turns, alpha, beta, dep, dep),
        ScenarioConfig("D-independent", n, turns, alpha, beta, indep, indep),
        ScenarioConfig("D-mismatch", n, turns, alpha, beta, dep, mismatch),
    ]


def evaluate_against_contract(summary: Dict[str, Dict[str, float]]) -> Dict[str, bool]:
    # Pre-registered criteria from manuscript.
    ok1 = summary["D-dependent"]["u_diff_cp_minus_base"] >= 0.05
    ok2 = summary["D-independent"]["u_diff_cp_minus_base"] >= -0.02
    ok3 = summary["D-dependent"]["osc_rate_cp"] <= 0.01
    return {
        "success_1_dep_gain": ok1,
        "success_2_indep_non_degrade": ok2,
        "success_3_stability": ok3,
        "overall_pass": ok1 and ok2 and ok3,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="NRR-Coupled synthetic reproducibility run")
    parser.add_argument("--seeds", type=int, default=30, help="Number of random seeds per scenario")
    parser.add_argument("--n", type=int, default=6, help="Number of candidates")
    parser.add_argument("--turns", type=int, default=60, help="Turns per run")
    parser.add_argument("--alpha", type=float, default=0.08, help="Base step size")
    parser.add_argument("--beta", type=float, default=0.6, help="Coupling gain")
    parser.add_argument(
        "--output",
        type=str,
        default="repro_summary.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    scenarios = build_scenarios(args.n, args.turns, args.alpha, args.beta)

    summary: Dict[str, Dict[str, float]] = {}
    for cfg in scenarios:
        rows = [run_once(cfg, seed=s) for s in range(args.seeds)]
        summary[cfg.name] = mean_dict(rows)

    contract = evaluate_against_contract(summary)

    payload = {
        "config": {
            "seeds": args.seeds,
            "n": args.n,
            "turns": args.turns,
            "alpha": args.alpha,
            "beta": args.beta,
        },
        "summary": summary,
        "contract": contract,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
