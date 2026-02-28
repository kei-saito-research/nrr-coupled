#!/usr/bin/env python3
"""NRR-Coupled v2 simulation harness.

Main design:
- Simulation-first (no LLM API).
- Same pre-defined operator sequence applied to uncoupled/coupled systems.
- Three dependency conditions: dependent / independent / mismatch.
- Coupled gain levels: beta in {0.1, 0.3, 0.5}.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


Operator = Tuple[str, int]


@dataclass(frozen=True)
class Pattern:
    name: str
    n: int
    w0: Tuple[float, ...]
    w_star: Tuple[float, ...]
    ops: Tuple[Operator, ...]
    a_dependent: Tuple[Tuple[float, ...], ...]


def clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def l1_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def zero_matrix(n: int) -> List[List[float]]:
    return [[0.0 for _ in range(n)] for _ in range(n)]


def negate_matrix(a: Sequence[Sequence[float]]) -> List[List[float]]:
    return [[-v for v in row] for row in a]


def make_dependency_matrix(n: int, pos: float, neg: float, side: float) -> Tuple[Tuple[float, ...], ...]:
    """Build a sparse mixed-sign dependency matrix.

    A[i][j] is influence from candidate j to i.
    """
    a = [[0.0 for _ in range(n)] for _ in range(n)]
    for j in range(n):
        a[(j + 1) % n][j] = pos
        a[(j + 2) % n][j] = neg
        a[(j - 1) % n][j] = side
    return tuple(tuple(row) for row in a)


def transfer_style_renormalize(u: Sequence[float], k: int) -> List[float]:
    """Transfer-v30 compatible normalization:
    keep target fixed, scale non-targets proportionally to fill residual mass.
    """
    n = len(u)
    out = [0.0] * n
    out[k] = u[k]

    residual = 1.0 - out[k]
    s_non = sum(u[i] for i in range(n) if i != k)

    if s_non <= 0.0:
        fill = residual / float(max(1, n - 1))
        for i in range(n):
            if i != k:
                out[i] = fill
        return out

    scale = residual / s_non
    for i in range(n):
        if i == k:
            continue
        out[i] = u[i] * scale

    # Tiny numerical drift correction.
    drift = 1.0 - sum(out)
    out[k] += drift
    return out


def update_step(
    w: Sequence[float],
    op: str,
    k: int,
    alpha: float,
    beta: float,
    a: Sequence[Sequence[float]],
    eps: float,
    umax: float,
) -> List[float]:
    u = list(w)

    delta = alpha if op == "sigma" else -alpha
    old_k = u[k]
    u[k] = clip(u[k] + delta, eps, umax)
    d = u[k] - old_k

    if beta > 0.0:
        for i in range(len(u)):
            if i == k:
                continue
            coeff = a[i][k]
            if coeff == 0.0:
                continue
            u[i] = clip(u[i] + beta * coeff * d, eps, umax)

    return transfer_style_renormalize(u, k)


def first_convergence_turn(distances: Sequence[float], conv_eps: float) -> int:
    for idx, d in enumerate(distances, start=1):
        if d <= conv_eps:
            return idx
    return len(distances) + 1


def count_oscillation_sign_flips(steps: Sequence[Sequence[float]], tol: float = 1e-15) -> int:
    if len(steps) < 2:
        return 0

    flips = 0
    n = len(steps[0])
    for t in range(1, len(steps)):
        prev = steps[t - 1]
        curr = steps[t]
        for i in range(n):
            if abs(prev[i]) <= tol or abs(curr[i]) <= tol:
                continue
            if prev[i] * curr[i] < 0.0:
                flips += 1
    return flips


def run_system(
    pattern: Pattern,
    condition: str,
    system: str,
    beta: float,
    a_condition: Sequence[Sequence[float]],
    alpha: float,
    conv_eps: float,
    eps: float,
    umax: float,
) -> Tuple[List[Dict[str, float]], Dict[str, float], List[List[float]]]:
    w = list(pattern.w0)
    n = pattern.n
    turns = len(pattern.ops)

    per_turn_rows: List[Dict[str, float]] = []
    distances: List[float] = []
    deltas: List[List[float]] = []
    trajectory: List[List[float]] = [w[:]]

    for t, (op, k) in enumerate(pattern.ops, start=1):
        next_w = update_step(w, op, k, alpha, beta, a_condition, eps, umax)
        dist = l1_distance(next_w, pattern.w_star)

        distances.append(dist)
        deltas.append([next_w[i] - w[i] for i in range(n)])
        trajectory.append(next_w[:])

        for i in range(n):
            per_turn_rows.append(
                {
                    "pattern": pattern.name,
                    "condition": condition,
                    "system": system,
                    "beta": beta,
                    "turn": t,
                    "candidate": i,
                    "weight": next_w[i],
                    "distance_to_w_star": dist,
                    "operator": op,
                    "target": k,
                }
            )

        w = next_w

    mean_dist = sum(distances) / turns
    terminal_dist = distances[-1]
    utility_u = 1.0 - (mean_dist / 2.0)
    conv_turn = first_convergence_turn(distances, conv_eps)
    osc_count = count_oscillation_sign_flips(deltas)
    osc_rate = osc_count / float(max(1, (turns - 1) * n))

    summary = {
        "pattern": pattern.name,
        "condition": condition,
        "system": system,
        "beta": beta,
        "turns": turns,
        "utility_u": utility_u,
        "mean_l1_dist": mean_dist,
        "terminal_l1_dist": terminal_dist,
        "convergence_turn": conv_turn,
        "oscillation_sign_flips": osc_count,
        "oscillation_rate": osc_rate,
    }
    return per_turn_rows, summary, trajectory


def build_patterns() -> List[Pattern]:
    ops4: Tuple[Operator, ...] = (
        ("sigma", 0), ("sigma", 1), ("delta", 3), ("sigma", 0), ("delta", 2), ("sigma", 0),
        ("sigma", 1), ("delta", 3), ("sigma", 0), ("delta", 2), ("sigma", 0), ("sigma", 1),
        ("delta", 3), ("sigma", 0), ("delta", 2), ("sigma", 0), ("sigma", 1), ("delta", 3),
        ("sigma", 0), ("delta", 2), ("sigma", 0), ("sigma", 1), ("delta", 3), ("sigma", 0),
    )

    ops5: Tuple[Operator, ...] = (
        ("sigma", 0), ("delta", 1), ("sigma", 2), ("delta", 4), ("sigma", 0), ("delta", 3),
        ("sigma", 2), ("delta", 1), ("sigma", 0), ("delta", 4), ("sigma", 2), ("delta", 3),
        ("sigma", 0), ("delta", 1), ("sigma", 2), ("delta", 4), ("sigma", 0), ("delta", 3),
        ("sigma", 2), ("delta", 1), ("sigma", 0), ("delta", 4), ("sigma", 2), ("delta", 3),
    )

    ops6: Tuple[Operator, ...] = (
        ("sigma", 0), ("sigma", 1), ("delta", 5), ("delta", 4), ("sigma", 2), ("delta", 3),
        ("sigma", 0), ("sigma", 1), ("delta", 5), ("delta", 4), ("sigma", 2), ("delta", 3),
        ("sigma", 0), ("sigma", 1), ("delta", 5), ("delta", 4), ("sigma", 2), ("delta", 3),
        ("sigma", 0), ("sigma", 1), ("delta", 5), ("delta", 4), ("sigma", 2), ("delta", 3),
    )

    return [
        Pattern(
            name="P1-n4",
            n=4,
            w0=(0.25, 0.25, 0.25, 0.25),
            w_star=(0.58, 0.24, 0.12, 0.06),
            ops=ops4,
            a_dependent=make_dependency_matrix(4, pos=0.70, neg=-0.45, side=0.25),
        ),
        Pattern(
            name="P2-n5",
            n=5,
            w0=(0.20, 0.20, 0.20, 0.20, 0.20),
            w_star=(0.44, 0.10, 0.28, 0.12, 0.06),
            ops=ops5,
            a_dependent=make_dependency_matrix(5, pos=0.65, neg=-0.40, side=0.20),
        ),
        Pattern(
            name="P3-n6",
            n=6,
            w0=(1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0),
            w_star=(0.30, 0.23, 0.19, 0.14, 0.09, 0.05),
            ops=ops6,
            a_dependent=make_dependency_matrix(6, pos=0.60, neg=-0.35, side=0.20),
        ),
    ]


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="NRR-Coupled v2 deterministic simulation")
    parser.add_argument("--alpha", type=float, default=0.08, help="Update step size")
    parser.add_argument("--conv-eps", type=float, default=0.12, help="Convergence distance threshold")
    parser.add_argument("--outdir", type=str, default="repro/results", help="Output directory")
    parser.add_argument("--indep-eq-tol", type=float, default=1e-12, help="Tolerance for D-independent equality check")
    args = parser.parse_args()

    beta_levels = [0.1, 0.3, 0.5]
    conditions = ["D-dependent", "D-independent", "D-mismatch"]
    patterns = build_patterns()

    eps = 1e-6
    umax = 1.0 - eps

    per_turn_rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []
    pair_rows: List[Dict[str, object]] = []
    indep_rows: List[Dict[str, object]] = []

    # Cache trajectories for independent-equality checks.
    indep_baseline_trajectories: Dict[str, List[List[float]]] = {}

    for pattern in patterns:
        a_dep = [list(r) for r in pattern.a_dependent]
        a_indep = zero_matrix(pattern.n)
        a_mismatch = negate_matrix(pattern.a_dependent)
        matrices = {
            "D-dependent": a_dep,
            "D-independent": a_indep,
            "D-mismatch": a_mismatch,
        }

        for condition in conditions:
            base_rows, base_summary, base_traj = run_system(
                pattern=pattern,
                condition=condition,
                system="uncoupled",
                beta=0.0,
                a_condition=zero_matrix(pattern.n),
                alpha=args.alpha,
                conv_eps=args.conv_eps,
                eps=eps,
                umax=umax,
            )
            per_turn_rows.extend(base_rows)
            summary_rows.append(base_summary)

            if condition == "D-independent":
                indep_baseline_trajectories[pattern.name] = base_traj

            for beta in beta_levels:
                cp_rows, cp_summary, cp_traj = run_system(
                    pattern=pattern,
                    condition=condition,
                    system="coupled",
                    beta=beta,
                    a_condition=matrices[condition],
                    alpha=args.alpha,
                    conv_eps=args.conv_eps,
                    eps=eps,
                    umax=umax,
                )
                per_turn_rows.extend(cp_rows)
                summary_rows.append(cp_summary)

                pair_rows.append(
                    {
                        "pattern": pattern.name,
                        "condition": condition,
                        "beta": beta,
                        "u_diff_cp_minus_base": cp_summary["utility_u"] - base_summary["utility_u"],
                        "mean_l1_diff_cp_minus_base": cp_summary["mean_l1_dist"] - base_summary["mean_l1_dist"],
                        "terminal_l1_diff_cp_minus_base": cp_summary["terminal_l1_dist"] - base_summary["terminal_l1_dist"],
                        "conv_turn_diff_cp_minus_base": cp_summary["convergence_turn"] - base_summary["convergence_turn"],
                        "osc_rate_diff_cp_minus_base": cp_summary["oscillation_rate"] - base_summary["oscillation_rate"],
                    }
                )

                if condition == "D-independent":
                    baseline_traj = indep_baseline_trajectories[pattern.name]
                    max_abs = 0.0
                    for t in range(len(cp_traj)):
                        for i in range(pattern.n):
                            diff = abs(cp_traj[t][i] - baseline_traj[t][i])
                            if diff > max_abs:
                                max_abs = diff
                    indep_rows.append(
                        {
                            "pattern": pattern.name,
                            "beta": beta,
                            "max_abs_diff": max_abs,
                            "tol": args.indep_eq_tol,
                            "pass": max_abs <= args.indep_eq_tol,
                        }
                    )

    # Aggregate rows for compact plotting/reporting.
    agg_rows: List[Dict[str, object]] = []
    for condition in conditions:
        for beta in beta_levels:
            rows = [r for r in pair_rows if r["condition"] == condition and abs(float(r["beta"]) - beta) < 1e-12]
            m_u = sum(float(r["u_diff_cp_minus_base"]) for r in rows) / len(rows)
            m_conv = sum(float(r["conv_turn_diff_cp_minus_base"]) for r in rows) / len(rows)
            m_osc = sum(float(r["osc_rate_diff_cp_minus_base"]) for r in rows) / len(rows)
            agg_rows.append(
                {
                    "condition": condition,
                    "beta": beta,
                    "mean_u_diff_cp_minus_base": m_u,
                    "mean_conv_turn_diff_cp_minus_base": m_conv,
                    "mean_osc_rate_diff_cp_minus_base": m_osc,
                }
            )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    write_csv(
        outdir / "cp_v2_per_turn.csv",
        per_turn_rows,
        fieldnames=[
            "pattern",
            "condition",
            "system",
            "beta",
            "turn",
            "candidate",
            "weight",
            "distance_to_w_star",
            "operator",
            "target",
        ],
    )
    write_csv(
        outdir / "cp_v2_summary.csv",
        summary_rows,
        fieldnames=[
            "pattern",
            "condition",
            "system",
            "beta",
            "turns",
            "utility_u",
            "mean_l1_dist",
            "terminal_l1_dist",
            "convergence_turn",
            "oscillation_sign_flips",
            "oscillation_rate",
        ],
    )
    write_csv(
        outdir / "cp_v2_pairwise.csv",
        pair_rows,
        fieldnames=[
            "pattern",
            "condition",
            "beta",
            "u_diff_cp_minus_base",
            "mean_l1_diff_cp_minus_base",
            "terminal_l1_diff_cp_minus_base",
            "conv_turn_diff_cp_minus_base",
            "osc_rate_diff_cp_minus_base",
        ],
    )
    write_csv(
        outdir / "cp_v2_independent_check.csv",
        indep_rows,
        fieldnames=["pattern", "beta", "max_abs_diff", "tol", "pass"],
    )
    write_csv(
        outdir / "cp_v2_aggregate.csv",
        agg_rows,
        fieldnames=[
            "condition",
            "beta",
            "mean_u_diff_cp_minus_base",
            "mean_conv_turn_diff_cp_minus_base",
            "mean_osc_rate_diff_cp_minus_base",
        ],
    )

    # Contract checks for manuscript section 6.4.
    dep_b03 = [r for r in agg_rows if r["condition"] == "D-dependent" and abs(float(r["beta"]) - 0.3) < 1e-12][0]
    indep_b03 = [r for r in agg_rows if r["condition"] == "D-independent" and abs(float(r["beta"]) - 0.3) < 1e-12][0]
    dep_osc_b03 = [
        r
        for r in summary_rows
        if r["condition"] == "D-dependent" and r["system"] == "coupled" and abs(float(r["beta"]) - 0.3) < 1e-12
    ]
    dep_osc_mean_b03 = sum(float(r["oscillation_rate"]) for r in dep_osc_b03) / len(dep_osc_b03)

    contract = {
        "success_1_dep_gain_beta_0_3": float(dep_b03["mean_u_diff_cp_minus_base"]) > 0.0,
        "success_2_indep_non_degrade_beta_0_3": float(indep_b03["mean_u_diff_cp_minus_base"]) >= 0.0,
        "success_3_dep_osc_rate_beta_0_3": dep_osc_mean_b03 <= 0.35,
        "all_indep_equivalence_pass": all(bool(r["pass"]) for r in indep_rows),
    }

    payload = {
        "config": {
            "alpha": args.alpha,
            "conv_eps": args.conv_eps,
            "beta_levels": beta_levels,
            "conditions": conditions,
            "patterns": [p.name for p in patterns],
        },
        "contract": contract,
    }
    with (outdir / "cp_v2_report.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
