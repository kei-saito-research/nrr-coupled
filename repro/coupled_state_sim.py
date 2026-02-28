#!/usr/bin/env python3
"""NRR-Coupled dependency-consistency simulation.

Design goals:
- Remove tautological reference trajectory dependence.
- Evaluate cp via dependency consistency, not self-generated targets.
- Use multiple seed-fixed random operator streams.

Primary metrics:
1) Turn-wise dependency consistency violation rate.
2) Additional repair operator count needed after primary-only stream.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

Operator = Tuple[str, int]


@dataclass(frozen=True)
class Pattern:
    name: str
    n: int
    w0: Tuple[float, ...]
    primary_targets: Tuple[int, ...]
    a_dep: Tuple[Tuple[float, ...], ...]


def clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


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
        if i != k:
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
    a_model: Sequence[Sequence[float]],
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
            coeff = a_model[i][k]
            if coeff == 0.0:
                continue
            u[i] = clip(u[i] + beta * coeff * d, eps, umax)

    return transfer_style_renormalize(u, k)


def generate_stream(primary_targets: Sequence[int], turns: int, seed: int) -> List[Operator]:
    rng = random.Random(seed)
    stream: List[Operator] = []
    ptargets = list(primary_targets)
    for _ in range(turns):
        op = "sigma" if rng.random() < 0.5 else "delta"
        k = ptargets[rng.randrange(len(ptargets))]
        stream.append((op, k))
    return stream


def count_turnwise_violations(
    prev_w: Sequence[float],
    next_w: Sequence[float],
    op: str,
    target: int,
    a_eval: Sequence[Sequence[float]],
    tol: float,
) -> Tuple[int, int]:
    """Count directed-edge violations for a single turn.

    For each edge i <- target where A_eval[i,target] != 0:
      expected sign(step_i) = sign(A_eval[i,target]) * sign(op)
    violation if observed sign contradicts expectation beyond tol.
    """
    sign_op = 1.0 if op == "sigma" else -1.0

    violations = 0
    opportunities = 0
    n = len(prev_w)

    for i in range(n):
        coeff = a_eval[i][target]
        if i == target or coeff == 0.0:
            continue
        opportunities += 1
        expected = 1.0 if coeff > 0.0 else -1.0
        expected *= sign_op
        observed = next_w[i] - prev_w[i]
        if abs(observed) <= tol:
            violations += 1
            continue
        if observed * expected < -tol:
            violations += 1

    return violations, opportunities


def dependent_signal(i: int, w: Sequence[float], w0: Sequence[float], a_eval: Sequence[Sequence[float]], primaries: Set[int]) -> float:
    s = 0.0
    for j in primaries:
        coeff = a_eval[i][j]
        if coeff == 0.0:
            continue
        s += coeff * (w[j] - w0[j])
    return s


def repair_operator_count(
    w_start: Sequence[float],
    w0: Sequence[float],
    alpha: float,
    beta: float,
    a_model: Sequence[Sequence[float]],
    a_eval: Sequence[Sequence[float]],
    primaries: Set[int],
    eps: float,
    umax: float,
    signal_tol: float,
    max_repair_ops: int,
) -> int:
    """Greedy repair on non-primary candidates until consistency mismatch resolves."""
    w = list(w_start)
    n = len(w)

    dependents = [i for i in range(n) if i not in primaries]
    ops = 0

    for _ in range(max_repair_ops):
        best_i = -1
        best_mag = 0.0
        best_op = "sigma"

        for i in dependents:
            sig = dependent_signal(i, w, w0, a_eval, primaries)
            if abs(sig) <= signal_tol:
                continue

            shift_i = w[i] - w0[i]
            # Desired shift direction follows sign(sig).
            mismatch = shift_i * sig < -signal_tol
            if not mismatch:
                continue

            mag = abs(sig) + abs(shift_i)
            if mag > best_mag:
                best_mag = mag
                best_i = i
                best_op = "sigma" if sig > 0 else "delta"

        if best_i < 0:
            break

        w = update_step(w, best_op, best_i, alpha, beta, a_model, eps, umax)
        ops += 1

    return ops


def run_sample(
    pattern: Pattern,
    condition: str,
    stream: Sequence[Operator],
    alpha: float,
    beta: float,
    a_model: Sequence[Sequence[float]],
    a_eval: Sequence[Sequence[float]],
    eps: float,
    umax: float,
    step_tol: float,
    signal_tol: float,
    max_repair_ops: int,
) -> Tuple[List[Dict[str, object]], Dict[str, float]]:
    w = list(pattern.w0)
    primaries = set(pattern.primary_targets)

    per_turn_rows: List[Dict[str, object]] = []
    total_viol = 0
    total_opp = 0

    for t, (op, k) in enumerate(stream, start=1):
        next_w = update_step(w, op, k, alpha, beta, a_model, eps, umax)
        v, o = count_turnwise_violations(w, next_w, op, k, a_eval, tol=step_tol)
        total_viol += v
        total_opp += o

        for i in range(pattern.n):
            per_turn_rows.append(
                {
                    "pattern": pattern.name,
                    "condition": condition,
                    "system": "coupled" if beta > 0 else "uncoupled",
                    "beta": beta,
                    "turn": t,
                    "candidate": i,
                    "weight": next_w[i],
                    "operator": op,
                    "target": k,
                    "turn_violations": v,
                    "turn_opportunities": o,
                }
            )

        w = next_w

    viol_rate = (total_viol / total_opp) if total_opp > 0 else 0.0

    repair_ops = repair_operator_count(
        w_start=w,
        w0=pattern.w0,
        alpha=alpha,
        beta=beta,
        a_model=a_model,
        a_eval=a_eval,
        primaries=primaries,
        eps=eps,
        umax=umax,
        signal_tol=signal_tol,
        max_repair_ops=max_repair_ops,
    )

    summary = {
        "consistency_violation_rate": viol_rate,
        "violations": float(total_viol),
        "opportunities": float(total_opp),
        "repair_ops_needed": float(repair_ops),
    }
    return per_turn_rows, summary


def stats(vals: List[float]) -> Dict[str, float]:
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
            primary_targets=(0, 1),
            a_dep=make_dependency_matrix(4, pos=1.20, neg=-0.90, side=0.70),
        ),
        Pattern(
            name="P2-n5",
            n=5,
            w0=(0.20, 0.20, 0.20, 0.20, 0.20),
            primary_targets=(0, 1, 2),
            a_dep=make_dependency_matrix(5, pos=1.10, neg=-0.80, side=0.65),
        ),
        Pattern(
            name="P3-n6",
            n=6,
            w0=(1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6),
            primary_targets=(0, 1, 2),
            a_dep=make_dependency_matrix(6, pos=1.00, neg=-0.75, side=0.60),
        ),
    ]


def parse_levels(s: str) -> List[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="NRR-Coupled dependency-consistency simulation")
    parser.add_argument("--turns", type=int, default=12)
    parser.add_argument("--num-streams", type=int, default=15)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--beta-levels", type=str, default="0.1,0.3,0.5")
    parser.add_argument("--seed-base", type=int, default=20260228)
    parser.add_argument("--step-tol", type=float, default=1e-12)
    parser.add_argument("--signal-tol", type=float, default=1e-6)
    parser.add_argument("--max-repair-ops", type=int, default=30)
    parser.add_argument("--indep-eq-tol", type=float, default=1e-12)
    parser.add_argument("--outdir", type=str, default="repro/results")
    args = parser.parse_args()

    beta_levels = parse_levels(args.beta_levels)
    conditions = ["D-dependent", "D-independent", "D-mismatch"]
    patterns = build_patterns()

    eps = 1e-6
    umax = 1.0 - eps

    per_turn_rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []
    pair_rows: List[Dict[str, object]] = []
    indep_rows: List[Dict[str, object]] = []

    for p_idx, pattern in enumerate(patterns):
        a_dep = [list(r) for r in pattern.a_dep]
        a_zero = zero_matrix(pattern.n)
        a_neg = negate_matrix(pattern.a_dep)

        for s_idx in range(args.num_streams):
            seed = args.seed_base + 1000 * p_idx + s_idx
            stream = generate_stream(pattern.primary_targets, args.turns, seed)

            for condition in conditions:
                if condition == "D-dependent":
                    a_model = a_dep
                    a_eval = a_dep
                elif condition == "D-independent":
                    a_model = a_zero
                    a_eval = a_zero
                else:
                    a_model = a_neg
                    a_eval = a_dep

                # Baseline: uncoupled.
                base_turn, base_summary = run_sample(
                    pattern=pattern,
                    condition=condition,
                    stream=stream,
                    alpha=args.alpha,
                    beta=0.0,
                    a_model=a_zero,
                    a_eval=a_eval,
                    eps=eps,
                    umax=umax,
                    step_tol=args.step_tol,
                    signal_tol=args.signal_tol,
                    max_repair_ops=args.max_repair_ops,
                )
                per_turn_rows.extend(
                    dict(r, stream_id=s_idx, stream_seed=seed) for r in base_turn
                )
                summary_rows.append(
                    {
                        "pattern": pattern.name,
                        "condition": condition,
                        "stream_id": s_idx,
                        "stream_seed": seed,
                        "system": "uncoupled",
                        "beta": 0.0,
                        **base_summary,
                    }
                )

                for beta in beta_levels:
                    cp_turn, cp_summary = run_sample(
                        pattern=pattern,
                        condition=condition,
                        stream=stream,
                        alpha=args.alpha,
                        beta=beta,
                        a_model=a_model,
                        a_eval=a_eval,
                        eps=eps,
                        umax=umax,
                        step_tol=args.step_tol,
                        signal_tol=args.signal_tol,
                        max_repair_ops=args.max_repair_ops,
                    )
                    per_turn_rows.extend(
                        dict(r, stream_id=s_idx, stream_seed=seed) for r in cp_turn
                    )
                    summary_rows.append(
                        {
                            "pattern": pattern.name,
                            "condition": condition,
                            "stream_id": s_idx,
                            "stream_seed": seed,
                            "system": "coupled",
                            "beta": beta,
                            **cp_summary,
                        }
                    )

                    pair_rows.append(
                        {
                            "pattern": pattern.name,
                            "condition": condition,
                            "stream_id": s_idx,
                            "stream_seed": seed,
                            "beta": beta,
                            "delta_violation_rate": cp_summary["consistency_violation_rate"]
                            - base_summary["consistency_violation_rate"],
                            "delta_repair_ops": cp_summary["repair_ops_needed"] - base_summary["repair_ops_needed"],
                        }
                    )

                    if condition == "D-independent":
                        # Compare full trajectories from per-turn rows for strict equivalence.
                        # Extract cp/base weights by (turn,candidate).
                        idx_base = {(r["turn"], r["candidate"]): r["weight"] for r in base_turn}
                        idx_cp = {(r["turn"], r["candidate"]): r["weight"] for r in cp_turn}
                        max_abs = 0.0
                        for key, w_b in idx_base.items():
                            w_c = idx_cp[key]
                            d = abs(float(w_c) - float(w_b))
                            if d > max_abs:
                                max_abs = d
                        indep_rows.append(
                            {
                                "pattern": pattern.name,
                                "stream_id": s_idx,
                                "stream_seed": seed,
                                "beta": beta,
                                "max_abs_diff": max_abs,
                                "tol": args.indep_eq_tol,
                                "pass": max_abs <= args.indep_eq_tol,
                            }
                        )

    # Robustness aggregate.
    agg_rows: List[Dict[str, object]] = []
    for condition in conditions:
        for beta in beta_levels:
            rows = [r for r in pair_rows if r["condition"] == condition and abs(float(r["beta"]) - beta) < 1e-12]
            v = [float(r["delta_violation_rate"]) for r in rows]
            ro = [float(r["delta_repair_ops"]) for r in rows]
            sv = stats(v)
            sr = stats(ro)
            agg_rows.append(
                {
                    "condition": condition,
                    "beta": beta,
                    "samples": len(rows),
                    "delta_violation_mean": sv["mean"],
                    "delta_violation_sd": sv["sd"],
                    "delta_violation_min": sv["min"],
                    "delta_violation_max": sv["max"],
                    "delta_repair_mean": sr["mean"],
                    "delta_repair_sd": sr["sd"],
                    "delta_repair_min": sr["min"],
                    "delta_repair_max": sr["max"],
                    "repair_better_rate": sum(1 for x in ro if x < 0.0) / len(ro),
                    "violation_better_rate": sum(1 for x in v if x < 0.0) / len(v),
                }
            )

    dep03 = [r for r in agg_rows if r["condition"] == "D-dependent" and abs(float(r["beta"]) - 0.3) < 1e-12][0]
    ind03 = [r for r in agg_rows if r["condition"] == "D-independent" and abs(float(r["beta"]) - 0.3) < 1e-12][0]
    mis03 = [r for r in agg_rows if r["condition"] == "D-mismatch" and abs(float(r["beta"]) - 0.3) < 1e-12][0]

    contract = {
        "success_dep_violation_reduction_beta_0_3": float(dep03["delta_violation_mean"]) < 0.0,
        "success_dep_repair_reduction_beta_0_3": float(dep03["delta_repair_mean"]) < 0.0,
        "success_mismatch_penalty_beta_0_3": (
            float(mis03["delta_violation_mean"]) > 0.0
            and float(mis03["delta_repair_mean"]) > 0.0
        ),
        "success_independent_non_degrade_beta_0_3": (
            float(ind03["delta_violation_mean"]) >= 0.0
            and float(ind03["delta_repair_mean"]) >= 0.0
        ),
        "all_indep_equivalence_pass": all(bool(r["pass"]) for r in indep_rows),
    }

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    write_csv(
        outdir / "cp_consistency_per_turn.csv",
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
            "operator",
            "target",
            "turn_violations",
            "turn_opportunities",
        ],
    )
    write_csv(
        outdir / "cp_consistency_summary.csv",
        summary_rows,
        fieldnames=[
            "pattern",
            "condition",
            "stream_id",
            "stream_seed",
            "system",
            "beta",
            "consistency_violation_rate",
            "violations",
            "opportunities",
            "repair_ops_needed",
        ],
    )
    write_csv(
        outdir / "cp_consistency_pairwise.csv",
        pair_rows,
        fieldnames=[
            "pattern",
            "condition",
            "stream_id",
            "stream_seed",
            "beta",
            "delta_violation_rate",
            "delta_repair_ops",
        ],
    )
    write_csv(
        outdir / "cp_consistency_aggregate.csv",
        agg_rows,
        fieldnames=[
            "condition",
            "beta",
            "samples",
            "delta_violation_mean",
            "delta_violation_sd",
            "delta_violation_min",
            "delta_violation_max",
            "delta_repair_mean",
            "delta_repair_sd",
            "delta_repair_min",
            "delta_repair_max",
            "repair_better_rate",
            "violation_better_rate",
        ],
    )
    write_csv(
        outdir / "cp_consistency_independent_check.csv",
        indep_rows,
        fieldnames=["pattern", "stream_id", "stream_seed", "beta", "max_abs_diff", "tol", "pass"],
    )

    payload = {
        "config": {
            "turns": args.turns,
            "num_streams": args.num_streams,
            "alpha": args.alpha,
            "beta_levels": beta_levels,
            "seed_base": args.seed_base,
            "conditions": conditions,
            "patterns": [p.name for p in patterns],
        },
        "contract": contract,
    }
    with (outdir / "cp_consistency_report.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
