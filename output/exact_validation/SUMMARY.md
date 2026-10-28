# Measured benchmark results

Successful runs: 24/24. Errors: 0.

All methods within a case/seed share identical sampled demand and initial dispatch.
Each search starts with a fresh prefix cache. Initialization is excluded from search time.
Exhaustive methods are exact only over outage choices under this deterministic response policy.

| Case | Seed | Ramp | k | Method | Shed MW | Time s | Status |
|---|---:|---:|---:|---|---:|---:|---|
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | sequin | 452.7801707302616 | 3.9506165999991936 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | sequin-release | 452.7801707302616 | 0.8871393000008538 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | greedy-flow | 377.77356943334655 | 0.27199259999906644 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | greedy-shed | 452.7801707302616 | 3.1748379999989993 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | greedy-crit | 386.5883532827314 | 2.30161550000048 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | std | 375.00000100000045 | 14.303942200000165 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | perm | 452.7801707302616 | 16.31094049999956 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | enum | 452.7801707302616 | 28.575074300002598 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | sequin | 460.0620794299047 | 5.775726800005941 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | sequin-release | 460.0620794299047 | 1.2495006000026478 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | greedy-flow | 460.0620794299047 | 0.446178800004418 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | greedy-shed | 460.0620794299047 | 5.774045799997111 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | greedy-crit | 389.14564785196234 | 4.64527950000047 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | std | 375.00000100000074 | 19.754441999997653 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | perm | 380.6794763004138 | 20.426088100000925 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | enum | 460.0620794299047 | 37.135471399997186 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | sequin | 465.5449636294457 | 6.001119000000472 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | sequin-release | 465.5449636294457 | 1.0268993999998202 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | greedy-flow | 465.5449636294457 | 0.45098189999407623 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | greedy-shed | 465.5449636294457 | 4.237275400002545 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | greedy-crit | 391.3110334217103 | 3.7965531000008923 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | std | 375.0000009999999 | 19.171228700004576 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | perm | 391.5589329402048 | 20.020145100002992 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | enum | 465.5449636294457 | 34.39217980000103 | ok |
