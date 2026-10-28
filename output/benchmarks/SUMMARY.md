# Measured benchmark results

Successful runs: 54/54. Errors: 0.

All methods within a case/seed share identical sampled demand and initial dispatch.
Each search starts with a fresh prefix cache. Initialization is excluded from search time.
Exhaustive methods are exact only over outage choices under this deterministic response policy.

| Case | Seed | Ramp | k | Method | Shed MW | Time s | Status |
|---|---:|---:|---:|---|---:|---:|---|
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | sequin | 452.7801707302616 | 2.797005200001877 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | sequin-release | 452.7801707302616 | 0.40916119999747025 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 2 | greedy-flow | 377.77356743334633 | 0.15682769999693846 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 3 | sequin | 452.7801707302616 | 2.8622710999989067 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 3 | sequin-release | 452.7801707302616 | 0.3611961999995401 | ok |
| pglib_opf_case14_ieee__api | 0 | 0.1 | 3 | greedy-flow | 377.77356743334633 | 0.13737539999419823 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | sequin | 460.0620794299047 | 1.943253999997978 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | sequin-release | 460.0620794299047 | 0.28297770000062883 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 2 | greedy-flow | 460.0620794299047 | 0.10191599999961909 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 3 | sequin | 460.0620794299047 | 2.910059399997408 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 3 | sequin-release | 460.0620794299047 | 0.3723169000004418 | ok |
| pglib_opf_case14_ieee__api | 1 | 0.1 | 3 | greedy-flow | 460.0620794299047 | 0.095654700002342 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | sequin | 465.5449636294457 | 1.7236324999976205 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | sequin-release | 465.5449636294457 | 0.3109852000052342 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 2 | greedy-flow | 465.5449636294457 | 0.12625550000666408 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 3 | sequin | 465.5449636294457 | 2.5746718000009423 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 3 | sequin-release | 465.5449636294457 | 0.4302201000027708 | ok |
| pglib_opf_case14_ieee__api | 2 | 0.1 | 3 | greedy-flow | 465.5449636294457 | 0.1529590000063763 | ok |
| pglib_opf_case39_epri__api | 0 | 0.1 | 2 | sequin | 2169.7156560570525 | 4.675053599996318 | ok |
| pglib_opf_case39_epri__api | 0 | 0.1 | 2 | sequin-release | 2169.7156560570525 | 0.4206324000042514 | ok |
| pglib_opf_case39_epri__api | 0 | 0.1 | 2 | greedy-flow | 2169.7156560570525 | 0.3909990999964066 | ok |
| pglib_opf_case39_epri__api | 0 | 0.1 | 3 | sequin | 3069.7156560570534 | 8.200826100000995 | ok |
| pglib_opf_case39_epri__api | 0 | 0.1 | 3 | sequin-release | 3069.7156560570534 | 0.743409700000484 | ok |
| pglib_opf_case39_epri__api | 0 | 0.1 | 3 | greedy-flow | 3069.7156560570525 | 0.5726333999991766 | ok |
| pglib_opf_case39_epri__api | 1 | 0.1 | 2 | sequin | 2120.4976696013623 | 5.175428700000339 | ok |
| pglib_opf_case39_epri__api | 1 | 0.1 | 2 | sequin-release | 2120.4976696013623 | 0.47533239999756915 | ok |
| pglib_opf_case39_epri__api | 1 | 0.1 | 2 | greedy-flow | 2120.4976696013623 | 0.6657511999947019 | ok |
| pglib_opf_case39_epri__api | 1 | 0.1 | 3 | sequin | 3020.4976696013637 | 12.435841299993626 | ok |
| pglib_opf_case39_epri__api | 1 | 0.1 | 3 | sequin-release | 3020.4976696013637 | 1.3934305000002496 | ok |
| pglib_opf_case39_epri__api | 1 | 0.1 | 3 | greedy-flow | 3020.4976696013637 | 0.9971869000000879 | ok |
| pglib_opf_case39_epri__api | 2 | 0.1 | 2 | sequin | 2102.937230318961 | 6.719581099998322 | ok |
| pglib_opf_case39_epri__api | 2 | 0.1 | 2 | sequin-release | 2102.937230318961 | 0.611766499998339 | ok |
| pglib_opf_case39_epri__api | 2 | 0.1 | 2 | greedy-flow | 2102.937230318961 | 0.5864682999963406 | ok |
| pglib_opf_case39_epri__api | 2 | 0.1 | 3 | sequin | 3002.9372303189616 | 11.12090999999782 | ok |
| pglib_opf_case39_epri__api | 2 | 0.1 | 3 | sequin-release | 3002.9372303189616 | 0.8733696999988751 | ok |
| pglib_opf_case39_epri__api | 2 | 0.1 | 3 | greedy-flow | 3002.937230318962 | 0.6735291000004509 | ok |
| pglib_opf_case118_ieee__api | 0 | 0.1 | 2 | sequin | 1180.9112761648116 | 40.67639670000062 | ok |
| pglib_opf_case118_ieee__api | 0 | 0.1 | 2 | sequin-release | 1180.9112761648116 | 3.806927600002382 | ok |
| pglib_opf_case118_ieee__api | 0 | 0.1 | 2 | greedy-flow | 725.8306521703857 | 13.45190680000087 | ok |
| pglib_opf_case118_ieee__api | 0 | 0.1 | 3 | sequin | 1782.6827159510294 | 85.31827040000644 | ok |
| pglib_opf_case118_ieee__api | 0 | 0.1 | 3 | sequin-release | 1782.6827159510294 | 8.919612999998208 | ok |
| pglib_opf_case118_ieee__api | 0 | 0.1 | 3 | greedy-flow | 1782.4223467367428 | 29.173761499994725 | ok |
| pglib_opf_case118_ieee__api | 1 | 0.1 | 2 | sequin | 1286.9924226883797 | 60.778785000002244 | ok |
| pglib_opf_case118_ieee__api | 1 | 0.1 | 2 | sequin-release | 1286.9924226883797 | 6.444688600000518 | ok |
| pglib_opf_case118_ieee__api | 1 | 0.1 | 2 | greedy-flow | 1286.9924226883797 | 19.39608070000395 | ok |
| pglib_opf_case118_ieee__api | 1 | 0.1 | 3 | sequin | 1851.4026989079075 | 118.34854659999837 | ok |
| pglib_opf_case118_ieee__api | 1 | 0.1 | 3 | sequin-release | 1851.4026989079075 | 9.264910900004907 | ok |
| pglib_opf_case118_ieee__api | 1 | 0.1 | 3 | greedy-flow | 1850.681469883014 | 38.25045350000437 | ok |
| pglib_opf_case118_ieee__api | 2 | 0.1 | 2 | sequin | 1225.6060246814866 | 61.094646400000784 | ok |
| pglib_opf_case118_ieee__api | 2 | 0.1 | 2 | sequin-release | 1225.6060246814866 | 4.4129397999931825 | ok |
| pglib_opf_case118_ieee__api | 2 | 0.1 | 2 | greedy-flow | 1225.6060246814866 | 19.20297859999846 | ok |
| pglib_opf_case118_ieee__api | 2 | 0.1 | 3 | sequin | 1837.7215680188178 | 98.80456609999965 | ok |
| pglib_opf_case118_ieee__api | 2 | 0.1 | 3 | sequin-release | 1837.7215680188178 | 9.88050249999651 | ok |
| pglib_opf_case118_ieee__api | 2 | 0.1 | 3 | greedy-flow | 1837.1349597822875 | 37.91923750000569 | ok |
