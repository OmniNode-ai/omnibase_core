## v0.47.61 (2026-11-01)

### Release
- Cut omnibase-core from dev at 0.47.61 by the scheduled release train.
- 21 release-relevant commit(s) merged since v0.47.60.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.60
- feat: invariant_analysis, a blocking core check that plans carry an invariant analysis covering each active invariant (#2209)
- feat: contract_chain_coverage reports unbound transitions, graph edges, guard halves and loop exits (#2207)
- : lab_receipt contract names its private-source class by a suffix pattern, not by repository names (#2204)
- feat: lab_receipt facts carry a per-file comment_only flag (#2206)
- feat: typed lab_receipt DoD check type replaces the text pattern (#2205)
- feat: lab_receipt validator, a core check that a change that runs carries an installed-and-observed lab receipt for its exact head (#2202)
- refactor: move 14 URL literals into network_defaults.yaml (#2196)
- feat: five check runtimes resolve their nodes from a container (#2198)
- fix: a RuntimeLocal run reads its command and terminals with no consumer group on a bus that can (#2200)
- refactor: remove literal_timeout findings from model modules (#2197)
- refactor: in-memory event bus and stores come from the container providers (#2195)
- refactor: check runtimes resolve their nodes from a container (#2194)
- refactor: hosts, addresses and ports read from a packaged network defaults contract (#2190)
- refactor: 32 TopicBase members come from a packaged YAML contract (#2193)
- refactor: resilience timings come from a packaged contract (#2191)
- refactor: seven check runtimes resolve their nodes from a container (#2192)
- refactor: operational timeouts and health-check presets come from packaged contracts (#2189)
- refactor: move event topic constants to YAML contracts (#2188)
- docs: baselined-file-growth message names the bind-then-edit path (#2186)
- refactor: canonical location rules become a handler class with a typed request (#2185)
- refactor: default topologies from packaged YAML, drop dead ports (#2183)

