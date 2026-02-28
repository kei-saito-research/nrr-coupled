#!/usr/bin/env python3
"""NRR-Coupled v3 simulation harness.

Main idea:
- No API calls.
- Use many seed-fixed random operator streams.
- Compare uncoupled vs coupled under identical streams.
- Evaluate robustness over streams (mean/min/max/std).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

Operator = Tuple[str, int]


@dataclass(frozen=True)
class Pattern:
    name: str
    n: int
    w0: Tuple[float, ...]
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
    a = [[0.0 for _ in range(n)] for _ in range(n)]
    for j in range(n):
        a[(j + 1) % n][j] = pos
        a[(j + 2) % n][j] = neg
        a[(j - 1) % n][j] = side
    return tuple(tuple(row) for row in a)


def transfer_style_renormalize(u: Sequence[float], k: int) -> List[float]:
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


def generate_random_stream(n: int, turns: int, seed: int) -> List[Operator]:
    rng = random.Random(seed)
    stream: List[Operator] = []
    for _ in range(turns):
        op = "sigma" if rng.random() < 0.5 else "delta"
        k = rng.randrange(n)
        stream.append((op, k))
    return stream


def rollout(
    w0: Sequence[float],
    stream: Sequence[Operator],
    alpha: float,
    beta: float,
    a: Sequence[Sequence[float]],
    eps: float,
    umax: float,
) -> List[List[float]]:
    w = list(w0)
    traj = [w[:]]
    for op, k in stream:
        w = update_step(w, op, k, alpha, beta, a, eps, umax)
        traj.append(w[:])
    return traj


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


def summarize_system_vs_reference(
    traj: Sequence[Sequence[float]],
    ref_final: Sequence[float],
    conv_eps: float,
) -> Dict[str, float]:
    turns = len(traj) - 1
    n = len(traj[0])

    distances = [l1_distance(traj[t], ref_final) for t in range(1, turns + 1)]
    steps = [[traj[t][i] - traj[t - 1][i] for i in range(n)] for t in range(1, turns + 1)]

    mean_dist = sum(distances) / turns
    final_dist = distances[-1]
    tau = first_convergence_turn(distances, conv_eps)
    osc_count = count_oscillation_sign_flips(steps)
    osc_rate = osc_count / float(max(1, (turns - 1) * n))

    # U in [0,1] using simplex L1 upper bound 2.
    utility_u = 1.0 - (mean_dist / 2.0)

    return {
        "utility_u": utility_u,
        "mean_l1_dist": mean_dist,
        "terminal_l1_dist": final_dist,
        "convergence_turn": float(tau),
        "oscillation_sign_flips": float(osc_count),
        "oscillation_rate": osc_rate,
    }


def aggregate(rows: List[Dict[str, float]], key: str) -> Dict[str, float]:
    vals = [float(r[key]) for r in rows]
    if not vals:
        return {"mean": 0.0, "sd": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": sum(vals) / len(vals),
        "sd": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
    }


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_patterns() -> List[Pattern]:
    return [
        Pattern(
            name="P1-n4",
            n=4,
            w0=(0.25, 0.25, 0.25, 0.25),
            a_dependent=make_dependency_matrix(4, pos=1.20, neg=-0.90, side=0.70),
        ),
        Pattern(
            name="P2-n5",
            n=5,
            w0=(0.20, 0.20, 0.20, 0.20, 0.20),
            a_dependent=make_dependency_matrix(5, pos=1.10, neg=-0.80, side=0.65),
        ),
        Pattern(
            name="P3-n6",
            n=6,
            w0=(1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0),
            a_dependent=make_dependency_matrix(6, pos=1.00, neg=-0.75, side=0.60),
        ),
    ]


def parse_beta_levels(s: str) -> List[float]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return [float(p) for p in parts]


def main() -> None:
    parser = argparse.ArgumentParser(description="NRR-Coupled v3 robust simulation")
    parser.add_argument("--turns", type=int, default=12, help="Turns per operator stream")
    parser.add_argument("--num-streams", type=int, default=15, help="Number of random operator streams per pattern")
    parser.add_argument("--alpha", type=float, default=0.10, help="Update step size")
    parser.add_argument("--beta-true", type=float, default=0.5, help="Hidden true coupling used for reference trajectory")
    parser.add_argument("--beta-levels", type=str, default="0.1,0.3,0.5", help="Coupled beta levels")
    parser.add_argument("--conv-eps", type=float, default=0.25, help="Convergence threshold for tau")
    parser.add_argument("--seed-base", type=int, default=20260228, help="Base seed for stream generation")
    parser.add_argument("--indep-eq-tol", type=float, default=1e-12, help="Tolerance for D-independent equivalence")
    parser.add_argument("--outdir", type=str, default="repro/results", help="Output directory")
    args = parser.parse_args()

    beta_levels = parse_beta_levels(args.beta_levels)
    conditions = ["D-dependent", "D-independent", "D-mismatch"]
    patterns = build_patterns()

    eps = 1e-6
    umax = 1.0 - eps

    per_turn_rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []
    pair_rows: List[Dict[str, object]] = []
    indep_rows: List[Dict[str, object]] = []

    for p_idx, pattern in enumerate(patterns):
        a_dep = [list(r) for r in pattern.a_dependent]
        a_indep = zero_matrix(pattern.n)
        a_mismatch = negate_matrix(pattern.a_dependent)

        for s_idx in range(args.num_streams):
            stream_seed = args.seed_base + 1000 * p_idx + s_idx
            stream = generate_random_stream(pattern.n, args.turns, stream_seed)

            for condition in conditions:
                if condition == "D-dependent":
                    a_true = a_dep
                    a_model = a_dep
                elif condition == "D-independent":
                    a_true = a_indep
                    a_model = a_indep
                else:
                    a_true = a_dep
                    a_model = a_mismatch

                ref_traj = rollout(pattern.w0, stream, args.alpha, args.beta_true, a_true, eps, umax)
                ref_final = ref_traj[-1]

                base_traj = rollout(pattern.w0, stream, args.alpha, 0.0, zero_matrix(pattern.n), eps, umax)
                base_metrics = summarize_system_vs_reference(base_traj, ref_final, args.conv_eps)
                base_metrics.update(
                    {
                        "pattern": pattern.name,
                        "condition": condition,
                        "stream_id": s_idx,
                        "stream_seed": stream_seed,
                        "system": "uncoupled",
                        "beta": 0.0,
                    }
                )
                summary_rows.append(base_metrics)

                for t in range(1, args.turns + 1):
                    d = l1_distance(base_traj[t], ref_final)
                    op, target = stream[t - 1]
                    for i in range(pattern.n):
                        per_turn_rows.append(
                            {
                                "pattern": pattern.name,
                                "condition": condition,
                                "stream_id": s_idx,
                                "stream_seed": stream_seed,
                                "system": "uncoupled",
                                "beta": 0.0,
                                "turn": t,
                                "candidate": i,
                                "weight": base_traj[t][i],
                                "distance_to_ref_final": d,
                                "operator": op,
                                "target": target,
                            }
                        )

                for beta in beta_levels:
                    cp_traj = rollout(pattern.w0, stream, args.alpha, beta, a_model, eps, umax)
                    cp_metrics = summarize_system_vs_reference(cp_traj, ref_final, args.conv_eps)
                    cp_metrics.update(
                        {
                            "pattern": pattern.name,
                            "condition": condition,
                            "stream_id": s_idx,
                            "stream_seed": stream_seed,
                            "system": "coupled",
                            "beta": beta,
                        }
                    )
                    summary_rows.append(cp_metrics)

                    for t in range(1, args.turns + 1):
                        d = l1_distance(cp_traj[t], ref_final)
                        op, target = stream[t - 1]
                        for i in range(pattern.n):
                            per_turn_rows.append(
                                {
                                    "pattern": pattern.name,
                                    "condition": condition,
                                    "stream_id": s_idx,
                                    "stream_seed": stream_seed,
                                    "system": "coupled",
                                    "beta": beta,
                                    "turn": t,
                                    "candidate": i,
                                    "weight": cp_traj[t][i],
                                    "distance_to_ref_final": d,
                                    "operator": op,
                                    "target": target,
                                }
                            )

                    pair_rows.append(
                        {
                            "pattern": pattern.name,
                            "condition": condition,
                            "stream_id": s_idx,
                            "stream_seed": stream_seed,
                            "beta": beta,
                            "u_diff_cp_minus_base": cp_metrics["utility_u"] - base_metrics["utility_u"],
                            "mean_l1_diff_cp_minus_base": cp_metrics["mean_l1_dist"] - base_metrics["mean_l1_dist"],
                            "terminal_l1_diff_cp_minus_base": cp_metrics["terminal_l1_dist"] - base_metrics["terminal_l1_dist"],
                            "tau_diff_cp_minus_base": cp_metrics["convergence_turn"] - base_metrics["convergence_turn"],
                            "osc_rate_diff_cp_minus_base": cp_metrics["oscillation_rate"] - base_metrics["oscillation_rate"],
                        }
                    )

                    if condition == "D-independent":
                        max_abs = 0.0
                        for t in range(len(cp_traj)):
                            for i in range(pattern.n):
                                diff = abs(cp_traj[t][i] - base_traj[t][i])
                                if diff > max_abs:
                                    max_abs = diff
                        indep_rows.append(
                            {
                                "pattern": pattern.name,
                                "stream_id": s_idx,
                                "stream_seed": stream_seed,
                                "beta": beta,
                                "max_abs_diff": max_abs,
                                "tol": args.indep_eq_tol,
                                "pass": max_abs <= args.indep_eq_tol,
                            }
                        )

    # Aggregate robustness stats over all streams x patterns.
    agg_rows: List[Dict[str, object]] = []
    for condition in conditions:
        for beta in beta_levels:
            rows = [r for r in pair_rows if r["condition"] == condition and abs(float(r["beta"]) - beta) < 1e-12]
            u = aggregate(rows, "u_diff_cp_minus_base")
            tau = aggregate(rows, "tau_diff_cp_minus_base")
            osc = aggregate(rows, "osc_rate_diff_cp_minus_base")
            faster_rate = sum(1 for r in rows if float(r["tau_diff_cp_minus_base"]) < 0.0) / len(rows)
            worse_u_rate = sum(1 for r in rows if float(r["u_diff_cp_minus_base"]) < 0.0) / len(rows)
            agg_rows.append(
                {
                    "condition": condition,
                    "beta": beta,
                    "samples": len(rows),
                    "u_diff_mean": u["mean"],
                    "u_diff_sd": u["sd"],
                    "u_diff_min": u["min"],
                    "u_diff_max": u["max"],
                    "tau_diff_mean": tau["mean"],
                    "tau_diff_sd": tau["sd"],
                    "tau_diff_min": tau["min"],
                    "tau_diff_max": tau["max"],
                    "osc_diff_mean": osc["mean"],
                    "osc_diff_sd": osc["sd"],
                    "faster_rate": faster_rate,
                    "u_worse_rate": worse_u_rate,
                }
            )

    # Contract checks at beta=0.3
    dep_b03 = [r for r in agg_rows if r["condition"] == "D-dependent" and abs(float(r["beta"]) - 0.3) < 1e-12][0]
    ind_b03 = [r for r in agg_rows if r["condition"] == "D-independent" and abs(float(r["beta"]) - 0.3) < 1e-12][0]
    mis_b03 = [r for r in agg_rows if r["condition"] == "D-mismatch" and abs(float(r["beta"]) - 0.3) < 1e-12][0]

    contract = {
        "success_dep_tau_gain_beta_0_3": float(dep_b03["tau_diff_mean"]) < 0.0,
        "success_dep_u_gain_beta_0_3": float(dep_b03["u_diff_mean"]) > 0.0,
        "success_mismatch_penalty_beta_0_3": float(mis_b03["u_diff_mean"]) < 0.0,
        "success_independent_non_degrade_beta_0_3": float(ind_b03["u_diff_mean"]) >= 0.0,
        "all_indep_equivalence_pass": all(bool(r["pass"]) for r in indep_rows),
    }

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    write_csv(
        outdir / "cp_v3_per_turn.csv",
        per_turn_rows,
        fieldnames=[
            "pattern",
            "condition",
            "stream_id",
            "stream_seed",
            "system",
            "beta",
            "turn",
            "candidate",
            "weight",
            "distance_to_ref_final",
            "operator",
            "target",
        ],
    )
    write_csv(
        outdir / "cp_v3_summary.csv",
        summary_rows,
        fieldnames=[
            "pattern",
            "condition",
            "stream_id",
            "stream_seed",
            "system",
            "beta",
            "utility_u",
            "mean_l1_dist",
            "terminal_l1_dist",
            "convergence_turn",
            "oscillation_sign_flips",
            "oscillation_rate",
        ],
    )
    write_csv(
        outdir / "cp_v3_pairwise.csv",
        pair_rows,
        fieldnames=[
            "pattern",
            "condition",
            "stream_id",
            "stream_seed",
            "beta",
            "u_diff_cp_minus_base",
            "mean_l1_diff_cp_minus_base",
            "terminal_l1_diff_cp_minus_base",
            "tau_diff_cp_minus_base",
            "osc_rate_diff_cp_minus_base",
        ],
    )
    write_csv(
        outdir / "cp_v3_aggregate.csv",
        agg_rows,
        fieldnames=[
            "condition",
            "beta",
            "samples",
            "u_diff_mean",
            "u_diff_sd",
            "u_diff_min",
            "u_diff_max",
            "tau_diff_mean",
            "tau_diff_sd",
            "tau_diff_min",
            "tau_diff_max",
            "osc_diff_mean",
            "osc_diff_sd",
            "faster_rate",
            "u_worse_rate",
        ],
    )
    write_csv(
        outdir / "cp_v3_independent_check.csv",
        indep_rows,
        fieldnames=["pattern", "stream_id", "stream_seed", "beta", "max_abs_diff", "tol", "pass"],
    )

    payload = {
        "config": {
            "turns": args.turns,
            "num_streams": args.num_streams,
            "alpha": args.alpha,
            "beta_true": args.beta_true,
            "beta_levels": beta_levels,
            "conv_eps": args.conv_eps,
            "conditions": conditions,
            "patterns": [p.name for p in patterns],
            "seed_base": args.seed_base,
        },
        "contract": contract,
    }
    with (outdir / "cp_v3_report.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
