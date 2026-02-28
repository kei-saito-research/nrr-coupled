# NRR-Coupled (cp) Specification v3

## 0. Scope and Boundary
- `cp = NRR-Coupled`
- Target: deterministic state updates under candidate dependencies.
- Uncoupled baseline is inherited from Transfer (canonical reference).
- cp defines coupled propagation, complexity bounds, and simulation-first evaluation contract.

Claim boundary:
- Transfer: independent-candidate condition.
- cp: dependent-candidate condition.

LLM-client interface hypothesis:
- Keep `(sigma/delta, target)` unchanged.
- Change only client propagation.
- On interface parse failure, record `TRANSFER_PRINCIPLES_REEVAL_REQUIRED=true`.

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
    u[i] = clip(u[i] + beta * A[i, k_t] * d, epsilon, u_max)
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
Per turn (sparse):
- local: `O(1)`
- propagation: `O(deg_out(k_t))`
- renormalization: `O(n)`

Total: `O(n + deg_out(k_t))`
- dense-column worst case: `O(n)`
- naive full-matrix upper bound: `O(n^2)`

Memory:
- sparse: `O(n + nnz(A))`
- dense: `O(n^2)`

## 3. Simulation-First Robustness Protocol
Main experiment is simulation (no API).

### 3.1 Patterns and operator streams
- Patterns:
  - `P1-n4`, `P2-n5`, `P3-n6`
- For each pattern, generate `15` random operator streams with fixed seeds.
- Stream length: `12` turns.
- Same stream is applied to uncoupled and coupled clients.

### 3.2 Dependency conditions
- `D-dependent`: true `A_dep`, model `A_dep`
- `D-independent`: true `0`, model `0`
- `D-mismatch`: true `A_dep`, model `-A_dep`

Matrix generation:
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

Reference trajectory:
- hidden true coupling `beta_true = 0.5`

## 4. Metrics and Criteria
Distance to reference final state:
- `d_t = ||w_t - w_ref_T||_1`

Utility:
- `U = 1 - (1/(2T)) * sum_t d_t`, `T=12`

Convergence speed:
- `tau_eps = min t such that d_t <= eps`, `eps = 0.25`

Oscillation:
- sign-flip count in per-candidate step deltas.

Independent equivalence:
- `max_{t,i} |w_cp[t,i] - w_base[t,i]| <= 1e-12`

Pre-registered checks at `beta=0.3`:
- dependent: mean `Delta tau < 0`
- dependent: mean `Delta U > 0`
- mismatch: mean `Delta U < 0`
- independent: mean `Delta U >= 0` and equivalence pass

## 5. Output Artifacts
- script: `repro/coupled_state_sim.py`
- `repro/results/cp_v3_per_turn.csv`
- `repro/results/cp_v3_summary.csv`
- `repro/results/cp_v3_pairwise.csv`
- `repro/results/cp_v3_aggregate.csv`
- `repro/results/cp_v3_independent_check.csv`
- `repro/results/cp_v3_report.json`
