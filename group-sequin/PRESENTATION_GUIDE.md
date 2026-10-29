# Presentation speaking guide

The presentation has one cover plus 23 content slides. All measurements use the group model. The PDF is a separate full report.

## Slide 2: The paper: why failure order matters
Use the road-network analogy, then explain that power flows obey physical equations and cannot be arbitrarily routed. The defender is myopic. Cite Chio et al., ICCPS 2025, Sections 3-4, DOI 10.1145/3716550.3722029.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 3: The defender and its carried state
Power is in MW in this code. The original loss output divides by baseMVA. A generator can switch off completely. The group code permits later restart because it does not carry z. The paper describes no restart in Eq. 2f. No AC voltage, frequency, relay or transient simulation.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 4: Group implementation: code reading order
The first three files already existed upstream. New responses still use this repository's grid_model.defend. The earlier neighboring sequin package is only imported by the optional comparison phase.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 5: Why the two implementations differ
There are additional angle-box, negative-injection and RNG differences in the report. No single factor is established as the cause of every mismatch. The six supplied cases have zero quadratic costs and active shunts, so those generic feature differences do not explain these measurements.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 6: The same attack can produce different loss
This is a model-comparison example, not a quality ranking. Different dispatch choices, shutdown/restart semantics and numerical settings can alter later ramp states. Default-compatibility replay of the new defender against untouched upstream source gives exactly matching generation and service on all 26 probes.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 7: Original reproduction rerun
The failed prefix is [83,5,19,228,196,177,212,219]. The original driver skipped the unsuccessful response. Case-14 guided results match selected reference budgets. Case-39 guided k=6 differs by about -2.075%, slightly beyond its 2% checker threshold. Full benchmark rows and the recorded solver status remain in results/. This does not establish exact reproduction of every paper result.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 8: Critique and the three extensions
The paper explicitly proposes ruggedization and variable epochs as future work in Section 6. Priority service is a realistic course-project extension with synthetic labels. Do not claim these general research ideas are invented here.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 9: Evaluation design
Protection has 1648 rows, timing 1728, and priority 23296. Row counts include deterministic repeats and policy comparisons. Protection design seeds 0/1/2 and held-out seeds 100-104 are separate. Other studies use demand seeds 0/1/2.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 10: Extension 1: adaptive line protection
Protection changes outage eligibility only. It leaves physical response on an eligible sequence unchanged, so filtering complete tables is valid. Exact outer protection enumeration for q<=2 is a separate small-instance oracle. Greedy has no general global guarantee.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 11: Protection on case 14
Lower loss is better. Each point averages held-out scenario worst losses, not a fixed common attack. At q=2 the scenario design helps substantially. At q=1 it fails to improve held-out worst loss, while the single-scenario plan does improve it. This is an important generalization caveat.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 12: Protection on case 39
Initial-flow protection slightly outperforms the robust design on held-out seeds at q=2. The scenario design improves more at q=3. Training-objective optimality does not establish the best unseen-scenario performance. Include both outcomes in the presentation.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 13: Protection under shifted conditions
A cell is a case, demand seed, ramp, demand spread and budget combination. Unperturbed seeds duplicate the same demand. Infeasible starting cases have no fabricated attack loss. The line plan remains frozen during stress evaluation.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 14: Extension 2: matched response windows
The simultaneous policy loses the whole set in the first window, then can respond twice more. Each window uses alpha Pmax times duration/5. Horizons are 7.5/15/30 minutes. Rates are derived assumptions, not equipment measurements.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 15: Timing: final MW and time weighting differ
The final-loss maximum and proxy-energy maximum may use different sequences. The snapshot proxy sums endpoint loss times duration, normalized by initial demand times horizon. It is not physical integration of continuous ramping. A worse final loss can still have a smaller proxy when it appears late.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 16: The energy measure and its limit
Say response-then-hold snapshot proxy every time you interpret MWh. Do not call it a validated blackout-energy forecast. Restore-load dynamics, continuous ramps and transient feasibility are future work.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 17: Extension 3: critical-service response
Group seed 17 selects positive-demand buses. Fractions are bus counts, not MW fractions, and assignments need not be nested. One group assignment per size is a limitation. The original total-service policy is retained as an extra comparison.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 18: Critical service at the nominal setting
Higher retention is better. Each policy is evaluated on exactly the same sequence set within a scenario. Case 14 is exhaustive. Cases 39/118 are sampled worst-found results, including critical-loss-targeted attacks. Rounded 100% retention is not a guarantee against unsearched attacks.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 19: Critical gains have costs and adverse cases
Give the full scenario and attack from priority_examples.json if asked. A negative gain means critical-first harmed later critical service. Myopic optimization maximizes service now, not across all future outages. Extra total loss can reflect a deliberate sacrifice of ordinary load.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 20: Priority outcomes across paired sequences
Do not interpret these counts as independent event probabilities. They include repeated configurations and demand scenarios. The matched-precision total-service control separates the policy objective from the default solver gap.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 21: Correctness and claim boundaries
The exported residual maximum is 1e-06 native row units. Residual checks validate the implemented mathematical constraints, not real-grid adequacy. Exact tables do not handle all dispatch ties or remove numerical MIP tolerances.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 22: What the results establish
Report improvement, inconclusion and failure honestly. None of these studies establishes broad real-world safety. The work completes the bounded second-part course-project scope.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 23: Future work motivated by the failures
Prioritize joint robust protection because stress failures were measured, and targeted critical search because the larger cohorts are small. Operator lookahead can test whether myopic choices explain adverse priority cases.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Slide 24: Demonstration and review route
If presenting live, run the saved demo first. Optimization is offline, so the browser only selects precomputed traces. Commands and artifact locations are in EXTENSIONS_README.md and PRESENTATION_GUIDE.md.
Source: group-sequin/results/extensions/; 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.

## Short project explanation
The paper finds damaging orders of line failures. Our group reproduces the response model and search. We then ask which lines to protect, how response time changes loss, and how to prioritize selected services. We rerun the measurements on the group model, report useful gains and failures, and preserve the scope limits.

## Before presenting
Use the exact same dataset and source version as the saved report. Treat large-grid cohort results as worst found. Do not equate a time-weighted snapshot proxy with continuous physical energy. Do not treat repeated deterministic rows as independent samples.