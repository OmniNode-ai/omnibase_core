=== Cursor Rule: Checklist Rule v4 - Enhanced Dependencies & Context ===

rule_id: "cursor_rule_checklist_v4"
title: "Checklist Rule v4 - Dependencies & Context Enhanced"
alias: ["checklist rule", "work ticket system", "agent-first tickets", "dependencies"]
status: "CANONICAL"
last_updated: "2025-01-04"
description: >
  Enhanced agent-first work ticket system with dependency tracking, blocker management,
  cross-references, and context preservation. Handles complex interconnected work streams
  where agents need to switch between checklists without losing context.

purpose:
  • Simple file-based ticket system with dependency awareness
  • Epic → Ticket hierarchy with cross-cutting relationships
  • Agent-first design with context preservation
  • Code proximity with cross-checklist navigation
  • Blocker identification and unblocking strategies
  • Progress tracking across dependent work streams

# === Directory Organization ===
ticket_organization:
  structure: "status_directories"  # Same at both levels

  node_level:
    location: "{node}/work_tickets/"
    subdirectories:
      - "active/"      # Currently being worked
      - "completed/"   # Finished work  
      - "blocked/"     # Waiting on dependencies
      - "backlog/"     # Planned but not started

  global_level:
    location: "work_tickets/"
    subdirectories:
      - "active/"      # Currently being worked
      - "completed/"   # Finished work
      - "blocked/"     # Waiting on dependencies  
      - "backlog/"     # Planned but not started
      - "epics/"       # Epic-level organization
      - "cross_cutting/" # NEW: Cross-epic dependencies and blockers

# === Enhanced Hierarchy ===
hierarchy:
  level_1: "Epic (strategic checklist .md file)"
  level_2: "Work Ticket (self-contained checklist .yaml file)"
  level_2_5: "NEW: Dependency Map (cross-cutting relationships)"
  # NO LEVEL 3/4 - Each ticket contains its own checklist

# === Naming ===
naming:
  epic_pattern: "{system}_{area}_checklist_{sequence:02d}_{scope}.md"
  ticket_pattern: "{area}_{sequence:03d}_{scope}.yaml"
  dependency_map_pattern: "dependencies_{scope}.yaml"

  components:
    area: "Domain area (e.g. nm_arch, core, cli, nr_event)"
    sequence: "Three-digit ID (e.g. 001, 002)"
    scope: "Brief description (e.g. model_split, validation)"

# === Enhanced Ticket Format ===
work_ticket_format:
  # Core metadata
  ticket_id: "nr_event_003_registry_handlers"
  epic: "nr_epic_001_event_driven_discovery"
  title: "Add Event Handlers to Node Registry"
  status: "active"  # Redundant with directory, but useful
  priority: "P0|P1|P2|P3"
  estimated_hours: 16

  # NEW: Dependency & Blocker Tracking
  dependencies:
    completed:
      - ticket_id: "nr_event_001_discovery_schemas"
        completion_date: "2025-01-03"
        notes: "Event models ready"
    pending:
      - ticket_id: "ng_mvp_007_generate_nodes"
        epic: "node_generator_epic"
        reason: "Need node_generator working to fix architecture violations"
    optional:
      - ticket_id: "performance_framework_setup"
        reason: "Would help with benchmarking but not blocking"

  blockers:
    - blocker_id: "chicken_egg_generator"
      description: "Node architecture fixes need node_generator working"
      severity: "high|medium|low"
      unblocking_ticket: "ng_mvp_007_generate_nodes"
      unblocking_epic: "node_generator_epic"
      workaround: "Implement functionality first, fix architecture on regeneration"
      estimated_delay_days: 3

  # NEW: Cross-References & Navigation
  relationships:
    same_epic: ["nr_event_002_introspection_publisher", "nr_event_004_discovery_protocol"]
    blocks: ["nr_event_005_mcp_integration", "nr_event_006_discovery_testing"]
    blocked_by: ["ng_mvp_007_generate_nodes"]
    related: ["architecture_cleanup_tickets"]

  # NEW: Context Preservation
  work_context:
    last_working_files:
      - "src/omnibase/nodes/node_registry/v1_0_0/tools/tool_registry_event_handler.py"
      - "src/omnibase/nodes/node_registry/v1_0_0/node.py"
    next_immediate_steps:
      - "Implement TOOL_DISCOVERY_REQUEST handling in handle_registry_event()"
      - "Add query filtering to _query_catalog() method"
    current_completion: "60%"
    critical_gaps:
      - "Missing discovery request/response workflow"
      - "No query filtering system"
    architecture_notes: "Direct tool instantiation in node.py violates ONEX - fix on regeneration"

  # Enhanced Checklist with Progress Indicators
  checklist:
    completed:
      - "[x] Add service_catalog data structure to NodeRegistry"
      - "[x] Implement handle_introspection_event()"
      - "[x] Implement handle_health_event() for status updates"
      - "[x] Implement handle_shutdown_event() for cleanup"
      - "[x] Add TTL logic to remove stale entries"
      - "[x] Add event subscriptions in __init__"
      - "[x] Thread-safe catalog operations"
    in_progress:
      - "[ ] **Implement handle_discovery_request() with query logic** ⚠️ CRITICAL GAP"
      - "[ ] **Create _query_catalog() with filter support** ⚠️ CRITICAL GAP"
    pending:
      - "[ ] Add correlation ID tracking for request/response"
      - "[ ] Comprehensive scenario tests (ONEX-compliant)"
      - "[ ] Performance benchmarks (< 10ms requirement)"
    deferred:
      - "[ ] Fix architecture violations (awaiting node_generator)"
      - "[ ] Protocol-based dependency injection (awaiting regeneration)"

# === NEW: Cross-Cutting Dependency Maps ===
dependency_map_format:
  # work_tickets/cross_cutting/dependencies_discovery_generator.yaml
  dependency_map_id: "discovery_generator_chicken_egg"
  description: "Node registry discovery work blocked by node generator completion"

  affected_epics:
    - epic_id: "nr_epic_001_event_driven_discovery"
      blocked_tickets: ["nr_event_003_registry_handlers"]
      workaround_strategy: "implement_functionality_first"
    - epic_id: "node_generator_epic"
      blocking_tickets: ["ng_mvp_007_generate_nodes"]
      priority: "unblock_discovery_work"

  resolution_strategies:
    primary:
      description: "Complete node_generator first"
      tickets: ["ng_mvp_007_generate_nodes"]
      estimated_timeline: "3-5 days"
    workaround:
      description: "Implement discovery functionality with architecture violations"
      acceptance: "temporary_until_regeneration"
      cleanup_tickets: ["architecture_fix_after_regeneration"]

# === Enhanced Agent Operations ===
agent_operations:
  # Original operations
  create: "Write YAML file to appropriate status directory"
  update: "Edit YAML file directly"
  move_status: "mv between status directories"
  list: "ls work_tickets/{status}/"
  read: "cat work_tickets/{status}/{ticket}.yaml"

  # NEW: Dependency operations
  dependency_chain: "Show full dependency chain for a ticket"
  blockers: "List all blockers for a ticket"
  unblock_strategy: "Show strategies to unblock a ticket"
  cross_references: "Show all related tickets across epics"

  # NEW: Context operations
  save_context: "Save current work state in work_context section"
  restore_context: "Load previous work state"
  switch_context: "Save current, load different ticket context"

  # NEW: Progress operations
  completion_percentage: "Calculate % complete for epic or ticket"
  critical_path: "Show critical path through dependencies"
  next_actionable: "Show tickets ready to work (no pending dependencies)"

# === Enhanced Validation ===
validation:
  required_fields: ["ticket_id", "epic", "title", "checklist"]
  recommended_fields: ["dependencies", "work_context", "relationships"]

  dependency_validation:
    - "All referenced tickets must exist"
    - "No circular dependencies allowed"
    - "Blocking relationships must be mutual"

  context_validation:
    - "Files in work_context must exist"
    - "Completion percentage must match checklist progress"

# === NEW: Context Switching Workflow ===
context_switching:
  save_current:
    - "Update work_context.last_working_files"
    - "Document next_immediate_steps"
    - "Note current_completion percentage"
    - "Update critical_gaps"

  switch_to_new:
    - "Load target ticket's work_context"
    - "Open last_working_files in editor"
    - "Review next_immediate_steps"
    - "Check for new blockers or dependencies"

  return_to_original:
    - "Restore from saved work_context"
    - "Check if dependencies are now resolved"
    - "Update progress based on other work completed"

# === Migration from v3 to v4 ===
migration:
  add_to_existing_tickets:
    - "dependencies: {completed: [], pending: [], optional: []}"
    - "blockers: []"
    - "relationships: {same_epic: [], blocks: [], blocked_by: [], related: []}"
    - "work_context: {last_working_files: [], next_immediate_steps: [], current_completion: '0%'}"

  create_dependency_maps:
    - "Identify cross-cutting blockers"
    - "Create cross_cutting/ directory"
    - "Document major chicken-egg problems"

  enhance_checklists:
    - "Group by completed/in_progress/pending/deferred"
    - "Add progress indicators (⚠️ for critical gaps)"
    - "Mark architecture violations vs functional requirements"

# === What We DON'T Have (Still Simple) ===
removed_features:
  - "Complex CLI with subcommands"
  - "Web dashboards and analytics"
  - "AI-powered suggestions"
  - "Visual dependency graphs"
  - "Resource allocation"
  - "Permission models"
  - "APIs (REST/GraphQL)"
  - "Webhooks"
  - "Audit trails"
  - "Sub-tickets (level 3/4)"
  - "Complex metadata beyond dependencies"

# === Benefits for Complex Work ===
benefits:
  context_preservation: "Never lose your place when switching between work streams"
  dependency_awareness: "Clear visibility into what blocks what"
  progress_tracking: "Understand completion across interconnected work"
  unblocking_strategies: "Clear paths to resolve chicken-egg problems"
  cross_epic_navigation: "Work spans multiple epics without losing relationships"
  workaround_documentation: "Accept temporary solutions with clear cleanup plans"

⸻
