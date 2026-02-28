# NRR-Coupled (cp) Specification v2

## 0. Scope and Boundary
- `cp = NRR-Coupled`
- Target: state updates when candidate dependencies exist.
- Uncoupled baseline is inherited from Transfer (canonical reference).
- cp defines only the coupled extension: propagation rule, complexity, and simulation evaluation contract.

Claim boundary:
- Transfer: independent-candidate condition.
- cp: dependent-candidate condition.

LLM-client interface (first hypothesis):
- Keep `(sigma/delta, target)` selection unchanged.
- Modify only client-side propagation.
- If parsing/interface fails, record `TRANSFER_PRINCIPLES_REEVAL_REQUIRED=true` and continue cp-side diagnosis.

## 1. State Representation
At turn `t`:
- candidate set `V = {1, ..., n}`
- weight vector `w_t in R^n`, `w_t[i] in [epsilon, u_max]`, `sum_i w_t[i] = 1`
- dependency matrix `A in R^{n x n}`, with `A[i,j]` = influence from candidate `j` to candidate `i`

Signs:
- `A[i,j] > 0`: reinforcing
- `A[i,j] < 0`: competitive
- `A[i,j] = 0`: no direct dependency

Hyperparameters:
- `alpha > 0`
- `beta in {0.1, 0.3, 0.5}` for coupled runs
- clipping bounds `epsilon`, `u_max`

## 2. Coupled Update Rule
Given operator `o_t in {sigma, delta}` and target `k_t`:

### 2.1 Local target update (Transfer-compatible)
```
Delta = +alpha if o_t = sigma else -alpha
u[k_t] = clip(w_t[k_t] + Delta, epsilon, u_max)
u[i] = w_t[i] for i != k_t
```

### 2.2 Coupled propagation (cp extension)
```
d = u[k_t] - w_t[k_t]
for i != k_t:
    u[i] = clip(u[i] + beta * A[i, k_t] * d, epsilon, u_max)
```

### 2.3 Transfer-style renormalization after propagation
```
w_{t+1}[k_t] = u[k_t]
S_non = sum_{i != k_t} u[i]
residual = 1 - w_{t+1}[k_t]
for i != k_t:
    w_{t+1}[i] = (u[i] / S_non) * residual
```
If `S_non == 0`, distribute residual uniformly over non-target candidates.

Rationale:
- This keeps Transfer normalization semantics when `beta=0`.
- cp differs only by propagation step, not by local operator interface.

## 3. Complexity Upper Bounds
Let `deg_out(k_t)` be nonzero count in column `k_t` of `A`.

Per turn:
- local update: `O(1)`
- sparse propagation: `O(deg_out(k_t))`
- renormalization: `O(n)`

Total:
- sparse optimized: `O(n + deg_out(k_t))`
- dense-column worst case: `O(n)`
- naive full-matrix upper bound: `O(n^2)`

Memory:
- sparse: `O(n + nnz(A))`
- dense: `O(n^2)`

## 4. Simulation Evaluation Contract (Main)
Main experiment direction is simulation-first (no LLM/API).

### 4.1 Fixed patterns and operator streams
- 3 fixed patterns:
  - `P1-n4` (`n=4`)
  - `P2-n5` (`n=5`)
  - `P3-n6` (`n=6`)
- Each pattern has a pre-defined 24-turn operator stream `(sigma/delta, target)`.
- The same stream is applied to uncoupled and coupled systems.

### 4.2 Dependency conditions
- `D-dependent`: nonzero dependency matrix with mixed reinforcing/competitive edges
- `D-independent`: `A = 0`
- `D-mismatch`: sign-inverted matrix `A = -A_dep`

Matrix generation rule:
- `A_dep[(j+1) mod n, j] = p_n`
- `A_dep[(j+2) mod n, j] = q_n < 0`
- `A_dep[(j-1) mod n, j] = s_n`
- others `0`

Pattern-specific coefficients:
- `P1-n4`: `(p_4, q_4, s_4) = (0.70, -0.45, 0.25)`
- `P2-n5`: `(p_5, q_5, s_5) = (0.65, -0.40, 0.20)`
- `P3-n6`: `(p_6, q_6, s_6) = (0.60, -0.35, 0.20)`

### 4.3 Compared systems
- uncoupled baseline: `beta = 0`
- coupled cp: `beta in {0.1, 0.3, 0.5}`

### 4.4 Metrics
Let `w*` be pre-defined target state.
- Distance per turn: `d_t = ||w_t - w*||_1`
- Utility:
  - `U = 1 - (1/(2T)) * sum_t d_t`
- Convergence speed:
  - `tau_eps = min t such that d_t <= eps` else `T+1`
- Oscillation:
  - sign-flip count in candidate-wise step deltas
- Independent equivalence:
  - `max_{t,i} |w_cp[t,i] - w_base[t,i]| <= 1e-12`

### 4.5 Falsifiable pass/fail checks
- C1: D-dependent at `beta=0.3`, mean `DeltaU > 0`
- C2: D-independent at `beta=0.3`, mean `DeltaU >= 0`
- C3: D-dependent at `beta=0.3`, mean oscillation rate `<= 0.35`
- C4: all D-independent equivalence checks pass

Failure is explicit if any criterion fails.

## 5. Artifacts
- Script: `repro/coupled_state_sim.py`
- Outputs:
  - `repro/results/cp_v2_per_turn.csv`
  - `repro/results/cp_v2_summary.csv`
  - `repro/results/cp_v2_pairwise.csv`
  - `repro/results/cp_v2_aggregate.csv`
  - `repro/results/cp_v2_independent_check.csv`
  - `repro/results/cp_v2_report.json`
