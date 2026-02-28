# NRR-Coupled (cp) Specification v6

## 0. Scope and Boundary
- `cp = NRR-Coupled`
- Target: dependent-candidate state updates.
- Uncoupled baseline is inherited from Transfer.
- cp defines coupled propagation and dependency-consistency evaluation.

Claim boundary:
- Transfer: independent-candidate condition
- cp: dependent-candidate condition

LLM-client interface:
- Keep `(sigma/delta, target)` unchanged.
- Change only client propagation.
- On parse failure: set `TRANSFER_PRINCIPLES_REEVAL_REQUIRED=true`.

## 1. Update Rule
Given operator `o_t in {sigma, delta}` and target `k_t`:

### 1.1 Local target update (Transfer-compatible)
```
Delta = +alpha if o_t = sigma else -alpha
u[k_t] = clip(w_t[k_t] + Delta, epsilon, u_max)
u[i] = w_t[i] for i != k_t
```

### 1.2 Coupled propagation (cp extension)
```
d = u[k_t] - w_t[k_t]
for i != k_t:
    u[i] = clip(u[i] + beta * A_model[i, k_t] * d, epsilon, u_max)
```

### 1.3 Transfer-style renormalization
```
out[k_t] = u[k_t]
residual = 1 - out[k_t]
S_non = sum(u[i] for i != k_t)
out[i] = (u[i] / S_non) * residual  for i != k_t
```
If `S_non == 0`, distribute residual uniformly over non-target candidates.

## 2. Complexity
Per turn:
- local update: `O(1)`
- sparse propagation: `O(deg_out(k_t))`
- renormalization: `O(n)`

Total sparse complexity:
- `O(n + deg_out(k_t))`

Upper bound with naive full-matrix use:
- `O(n^2)`

## 3. Evaluation Protocol (Non-circular)
Main design avoids coupled-generated target references.

### 3.1 Patterns and streams
- patterns: `P1-n4`, `P2-n5`, `P3-n6`
- per pattern: `15` random streams, seed-fixed
- stream length: `12`
- stream targets are restricted to primary candidates only

Primary sets:
- `P1-n4`: `{0,1}`
- `P2-n5`: `{0,1,2}`
- `P3-n6`: `{0,1,2}`

### 3.2 Condition matrices
- `D-dependent`: `A_model = A_dep`, `A_eval = A_dep`
- `D-independent`: `A_model = 0`, `A_eval = 0`
- `D-mismatch`: `A_model = -A_dep`, `A_eval = A_dep`

`A_dep` generation:
- `A_dep[(j+1) mod n, j] = p_n`
- `A_dep[(j+2) mod n, j] = q_n < 0`
- `A_dep[(j-1) mod n, j] = s_n`
- others `0`

Coefficients:
- `P1-n4`: `(p_4, q_4, s_4) = (1.20, -0.90, 0.70)`
- `P2-n5`: `(p_5, q_5, s_5) = (1.10, -0.80, 0.65)`
- `P3-n6`: `(p_6, q_6, s_6) = (1.00, -0.75, 0.60)`

### 3.3 Compared systems
- uncoupled baseline: `beta = 0`
- coupled cp: `beta in {0.1, 0.3, 0.5}`

## 4. Metrics
### M1: dependency-consistency violation rate
At turn `t` with target `k_t` and op sign `s_t`:
- expected sign for edge `i <- k_t`:
  - `sign(delta_w_i) = sign(A_eval[i,k_t]) * s_t`
- contradiction counts as violation.
- rate = violations / opportunities.
- if `abs(delta_w_i) <= tol`, the turn is conservatively counted as violation
  (includes clipping-saturation zero-movement cases).
- in `D-independent`, `A_eval=0` so opportunities are zero and this metric is
  bookkeeping-only; strict trajectory equality is the substantive check.

### M2: additional repair operator count
After primary stream, run greedy repairs on non-primary candidates.
- signal for candidate `i`:
  - `signal_i = sum_{j in primaries} A_eval[i,j] * (w_j - w0_j)`
- if `sign(w_i - w0_i)` opposes `sign(signal_i)`, candidate is mismatched.
- apply `sigma`/`delta` to largest mismatch until resolved or max budget.
- count additional repair ops.
- repair budget cap is `max_repair_ops=30`; cap hits imply reported repair
  degradation may be a lower bound.

Pairwise deltas:
- `DeltaV = V_cp - V_base`
- `DeltaR = R_cp - R_base`

Negative is better for cp.

## 5. Pre-registered Checks (beta=0.3)
- dependent: mean `DeltaV < 0`
- dependent: mean `DeltaR < 0`
- mismatch: mean `DeltaV > 0` and mean `DeltaR > 0`
- independent: exact equivalence pass (`max_abs_diff <= 1e-12`)

## 6. Output Artifacts
- `repro/coupled_state_sim.py`
- `repro/results/cp_consistency_per_turn.csv`
- `repro/results/cp_consistency_summary.csv`
- `repro/results/cp_consistency_pairwise.csv`
- `repro/results/cp_consistency_aggregate.csv`
- `repro/results/cp_consistency_independent_check.csv`
- `repro/results/cp_consistency_report.json`
