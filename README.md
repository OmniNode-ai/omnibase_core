# omnibase_core

omnibase_core provides the contracts, models, validation and execution primitives for the ONEX framework.
Documentation: [knowledge_base](https://github.com/OmniNode-ai/knowledge_base).

## v0.47.61 (2026-11-01)

### Release
- Cut omnibase-core from dev at 0.47.61 by the scheduled release train.
- 23 release-relevant commit(s) merged since v0.47.60.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.60
- move the diagram-drift check into omnibase_core as a generic validator (#2216)
- feat: refuse a PR that cites only a parent ticket, require repo-evidence / dod-verify (#2215)
- feat: invariant_analysis, a blocking core check that plans carry an invariant analysis covering each active invariant (#2209)
- feat: contract_chain_coverage reports unbound transitions, graph edges, guard halves and loop exits (#2207)
- lab_receipt contract names its private-source class by a suffix pattern, not by repository names (#2204)
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

## v0.47.60 (2026-10-31)

### Release
- Cut omnibase-core from dev at 0.47.60 by the scheduled release train.
- 7 release-relevant commit(s) merged since v0.47.59.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.59
- feat: a machine row binds the grant roles it holds by name (#2178)
- fix: core help states one job per command and names onex setup as the quickstart (#2177)
- feat: a developer.principal row may declare that its principal is a machine (#2176)
- feat: contracts_and_di checker in the generic validator format (stage 1, not wired) (#2175)
- feat: the PR OCC stamp schema returns to omnibase_core as omnibase_compat retires (#2173)
- feat: collaborator_lane validator refuses collaborator work sent to the dev lane (#2171)
- feat: ModelNodeAnnouncement, canonical content hash, pure node catalog and admission (#2169)

## v0.47.59 (2026-10-30)

### Release
- Cut omnibase-core from dev at 0.47.59 by the scheduled release train.
- 3 release-relevant commit(s) merged since v0.47.58.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.58
- fix: shipped contracts name the producer of each externally produced topic (#2166)
- feat: dev_tag_lineage validator verifies a dev-merge tag source in the generic format (#2164)
- K1 handler_di checker in the generic validator format, replacing handler_di_gate (#2144)

## v0.47.58 (2026-10-29)

### Release
- Cut omnibase-core from dev at 0.47.58 by the scheduled release train.
- 12 release-relevant commit(s) merged since v0.47.57.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.57
- T4.1a: hardcoded_model_config families T (tier aliases) and N (engine names) (#2121)
- T-Q6: K7 validator_home, K10 checker_rule_data, generic-format refusal, one-off migration (#2122)
- T-B1b: binding conformance check moved to omnibase_core (#2119)
- T-P1b: design-record check as a core checker (#2118)
- T0.1: private vocabulary resolution as a node, handler resolved from the container (#2110)
- T1.1 support: node-home admits declared validator nodes (#2123)
- T2.6: check-only hooks and the hook-writes rule (#2112)
- T2.1: core hook ids and shrink-only baselines for dict-any and backward-compat (#2113)
- T0.2: pin parity for the shared core hook repo (#2111)
- feat: action-pin rule in the generic validator format, first-party refs by dev-merge tag (#2106)
- feat: sibling pins carry a staleness bound and each dev merge opens the dependency-pin bump in listed consumers (#2105)
- feat: the FSM executor evaluates every operator the condition model accepts (#2103)

## v0.47.55 (2026-10-24)

### Release
- Cut omnibase-core from dev at 0.47.55 by the scheduled release train.
- 2 release-relevant commit(s) merged since v0.47.54.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.54
- feat: every baselined file only shrinks, on every surface (#2087)
- feat: canonical file shape refuses TypeScript outside its locations and shell scripts everywhere (#2088)

## v0.47.53 (2026-10-22)

### Release
- Cut omnibase-core from dev at 0.47.53 by the scheduled release train.
- 1 release-relevant commit(s) merged since v0.47.52.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.52
- feat: the terminal cause enum gains returned_to_caller (#2081)

## v0.47.52 (2026-10-22)

### Release
- Cut omnibase-core from dev at 0.47.52 by the scheduled release train.
- 4 release-relevant commit(s) merged since v0.47.51.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.51
- fix: ticket contract dod_evidence items accept ac_bindings (#2076)
- feat: public runner placement check runs with no baseline (#2072)
- feat: shrink-only CI inheritance baseline and validator-triggered bus event (#2071)
- fix: replace asyncio.iscoroutinefunction with inspect variant (#2075)

## v0.47.51 (2026-10-20)

### Release
- Cut omnibase-core from dev at 0.47.51 by the scheduled release train.
- 2 release-relevant commit(s) merged since v0.47.50.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.50
- feat: the ticket contract item declares supersedes_ac_binding (#2067)
- refactor(runtime): subscribe to terminal topics concurrently (#2064)

## v0.47.50 (2026-10-20)

### Release
- Cut omnibase-core from dev at 0.47.50 by the scheduled release train.
- 2 release-relevant commit(s) merged since v0.47.49.
- Opened by the release train, which cuts only when the repo's declared lab-evidence premise holds for the exact candidate commit.

### Included Since v0.47.49
- fix: cascade legs and CI Summary stop going red on a release head (#2062)
- feat: the delegation wire request admits the context_compaction task class (#2061)
