Stand-in for the text of plan section 11.3 (the design record of the plan's first
mechanism). The lab host that built this node could not read the plan; replace this
file with the verbatim section text before relying on AC3.

Intended state: every plan reported by the plan-write skill carries a design record that the checker passes, read as exit_code 0 on the plan text.
Live check command: onex run-node node_design_record_check_compute --input plan.json
Live check failing reading: exit_code 1 on a plan with an empty failure-mode table, read before the build.
Live check healthy reading: exit_code 0.
Live check reader: the plan-write skill, on every plan.
Live check cadence: each plan write.

| Failure mode | How it happens | Detected by | Severity | Detector |
| -- | -- | -- | -- | -- |
| Plan reported without running the checker | the skill step is skipped | none | 2 | GAP |
| Checker passes a plan with an empty table | parser misses the table | pytest case on an empty table | 3 | tests/nodes/node_design_record_check_compute/test_check_design_record.py |
| Severity outside the configured levels | row written with severity 4 | pytest case on severity 4 | 1 | tests/nodes/node_design_record_check_compute/test_check_design_record.py |
