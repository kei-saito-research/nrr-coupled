# NRR-Coupled (cp) Specification v1

## 0. Scope and Boundary
- `cp = NRR-Coupled`.
- Target condition: state update when dependencies exist across candidates.
- Uncoupled baseline definition is inherited from Transfer and treated as canonical reference.
- This document defines only the coupled extension: propagation rule, complexity upper bounds, and evaluation boundary.

Boundary of claims:
- Transfer: independent-candidate condition.
- cp: dependent-candidate condition.

LLM-client interface first hypothesis:
- Keep `sigma`/`delta` selection interface unchanged.
- Change only client-side propagation rule.
- If interface mismatch or instability is observed, record `TRANSFER_PRINCIPLES_REEVAL_REQUIRED=true` and continue cp design/testing.

## 1. State Representation
At turn `t`, state is:
- candidate set `V = {1, ..., n}`
- weight vector `w_t in R^n`, with `w_t[i] >= epsilon`, `sum_i w_t[i] = 1`
- dependency matrix `A in R^{n x n}` where `A[i,j]` is influence from candidate `j` to candidate `i`
  - `A[i,j] > 0`: reinforcing relation
  - `A[i,j] < 0`: competitive relation
  - `A[i,j] = 0`: no direct dependency

Hyperparameters:
- base step size `alpha > 0`
- coupling gain `beta >= 0`
- clipping bounds `epsilon in (0, 1/n)`, `u_max <= 1 - epsilon`

## 2. Coupled Update Rule
Given operator `o_t in {sigma, delta}` and target index `k_t` from LLM:

### 2.1 Local update (same interface as Transfer)
```
Delta_k = +alpha    if o_t = sigma
Delta_k = -alpha    if o_t = delta
u = w_t
u[k_t] = clip(w_t[k_t] + Delta_k, epsilon, u_max)
```

### 2.2 Coupled propagation (new in cp)
```
d = nu[k_t] - w_t[k_t]
for each i != k_t:
    nu[i] = clip(nu[i] + beta * A[i, k_t] * d, epsilon, u_max)
```

### 2.3 Renormalization
```
S = sum_i nu[i]
w_{t+1}[i] = nu[i] / S
```

## 3. Complexity Upper Bounds
Let `deg_out(k_t)` be number of non-zero elements in column `k_t` of `A`.

Per turn:
- Local update: `O(1)`
- Coupled propagation (sparse): `O(deg_out(k_t))`
- Renormalization: `O(n)`

Total per turn:
- Optimized sparse implementation: `O(n + deg_out(k_t))`
- Dense worst case (`deg_out(k_t)=n-1`): `O(n)`
- Naive full-matrix implementation upper bound: `O(n^2)`

Memory:
- `O(n + nnz(A))` with sparse matrix
- `O(n^2)` with dense matrix

## 4. Applicability and Failure Conditions

### 4.1 Applicability (must hold)
1. Candidate set is finite and explicitly trackable.
2. Dependency structure is known or estimable as bounded matrix `A`.
3. Update decision remains directional (`sigma`/`delta`) without changing LLM API contract.
4. Coupling strength is bounded so that update remains stable in observed runs.

### 4.2 Failure conditions (must report)
1. **Oscillation/instability**: repeated sign-flipping or large L1 drift above threshold.
2. **Over-coupling collapse**: one candidate dominates due to excessive `beta` or mis-specified `A`.
3. **Mismatched dependency graph**: cp underperforms uncoupled baseline on dependency-heavy tasks.
4. **Interface break**: LLM output cannot be parsed to valid `(sigma/delta, target)` pair.

On failure (3) or (4), set:
```
TRANSFER_PRINCIPLES_REEVAL_REQUIRED=true
```
and continue cp-side analysis.

## 5. Evaluation Contract (Falsifiable)
Primary comparison is paired:
- Uncoupled baseline (Transfer reference implementation)
- Coupled extension (cp)

Success criteria (must be falsifiable):
1. In dependency-present scenarios, cp improves utility metric by at least preset threshold.
2. In independent scenarios, cp does not materially degrade against uncoupled baseline.
3. Instability rate remains below preset threshold.

Failure criteria (explicit):
1. cp fails to exceed threshold in dependency-present scenarios.
2. cp degrades beyond tolerance in independent scenarios.
3. instability rate exceeds threshold.

All thresholds must be fixed before evaluation and not tuned after inspecting outcomes.
