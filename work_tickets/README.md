# Work Tickets Directory

This directory manages work tickets for the ONEX Core framework project using a structured workflow.

## Directory Structure

```
work_tickets/
├── active/      # Currently active work tickets
├── backlog/     # Planned future work tickets  
├── completed/   # Finished work tickets
└── archive/     # Long-term storage for old tickets
```

## Workflow States

### `backlog/`
- **Purpose**: Planning and prioritization
- **Contents**: Future work items, feature requests, technical debt
- **Status**: Not yet started, awaiting prioritization

### `active/`
- **Purpose**: Current development focus
- **Contents**: Work tickets currently being developed
- **Status**: In progress, assigned to developers

### `completed/`
- **Purpose**: Recently finished work
- **Contents**: Completed tickets for reference and validation
- **Status**: Done, tested, merged

### `archive/`
- **Purpose**: Long-term storage
- **Contents**: Old completed tickets, cancelled work, historical records
- **Status**: Historical reference only

## Ticket Management

### Moving Between States
```bash
# Start work on a backlog item
mv work_tickets/backlog/TICKET-001.md work_tickets/active/

# Complete active work
mv work_tickets/active/TICKET-001.md work_tickets/completed/

# Archive old completed work
mv work_tickets/completed/TICKET-001.md work_tickets/archive/
```

### Ticket Naming Convention
- Format: `TICKET-XXX-brief-description.md`
- Example: `TICKET-001-implement-node-base-classes.md`
- Sequential numbering for easy tracking

## Integration with ONEX Ecosystem

This structure aligns with the broader ONEX project management approach and supports:
- **Velocity Tracking**: Measure development progress
- **Sprint Planning**: Organize work into development cycles  
- **Technical Debt Management**: Track and prioritize improvements
- **Documentation**: Maintain development history and decisions

## Usage Notes

- Keep ticket descriptions concise but complete
- Include acceptance criteria and testing requirements
- Reference related issues, dependencies, and architectural decisions
- Update ticket status promptly as work progresses