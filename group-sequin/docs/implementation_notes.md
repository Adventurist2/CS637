# What this simple implementation can claim

## 1. What is implemented

We did not rewrite the whole Julia repository.We implemented the parts needed for a small independent check:

- read MATPOWER bus / generator / branch data;
- solve an intact DC OPF;
- remove transmission lines;
- solve the defender's maximum-load-served problem after each failure;
- carry generator output and already-served load to the next round;
- exact simultaneous search for small `k`;
- exact ordered sequential search for small cases;
- greedy immediate-impact search;
- a small guided search which only tests high-flow candidate lines.

The code is deliberately plain Python + NumPy/SciPy.

## 2. Strong reproduction: Case 14, k=2

| method | final load shed (p.u.) | sequence / set |
|---|---:|---|
| exact simultaneous N-2 | 3.7500 | (1, 17) |
| exact ordered sequential | 4.3997 | (3, 1) |
| simple guided search | 4.3997 | (3, 1) |

This independently supports the paper's central claim: letting the system respond between failures changes the outcome, and a guided sequential search can recover the exact small-case optimum.

## 3. Strong cross-check: Case 39

| k | method | our Python | author reference | difference |
|---:|---|---:|---:|---:|
| 2 | greedy impact | 20.9392 | 20.9392 | ~0% |
| 2 | guided | 20.9392 | 20.9392 | ~0% |
| 3 | greedy impact | 28.7502 | 28.7502 | ~0% |
| 3 | guided | 29.9392 | 29.9392 | ~0% |
| 4 | greedy impact | 36.3411 | 35.9122 | +1.19% |
| 4 | guided | 55.4702 | 56.0850 | -1.10% |

## 4. Partial reproduction: ramping study

The intentionally simpler ramp model agrees at ramp = 1.0, but diverges strongly under tight ramping because it omits the binary generator shut-down choice used by the full formulation. This is therefore labelled **partial reproduction / modelling limitation**.

## 5. Computational limitation

Exact Case-39 enumeration for k=3 needs `46 x 45 x 44 = 91,080` ordered sequences. Each sequence contains three defender optimizations, so exact enumeration is kept to Case 14 in this compact implementation.

This is mainly an LP/MILP and combinatorial-search workload, not a GPU problem.

## 6. Interpretation notes

> We first ran the authors' released implementation as an artifact check. For the implementation component, we then wrote a compact independent Python/SciPy model containing the DC grid constraints, sequential defender state propagation, exact small-case search, greedy impact, and a SEQUIN-style guided search. On Case 14, the guided method recovered the same 4.3997 p.u. result as exhaustive ordered search, compared with 3.75 p.u. for simultaneous N-2. On Case 39, our k=2 and k=3 results match selected released reference values and the k=4 results are within about 1.2%. We also report the simplified ramping formulation as a partial reproduction rather than claiming full agreement.
