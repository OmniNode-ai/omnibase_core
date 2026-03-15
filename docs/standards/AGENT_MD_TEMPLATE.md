# AGENT.md Template

Canonical template for AGENT.md files across all ONEX repos. AGENT.md is an LLM navigation index -- it tells agents where to look, not what is there.

## Rules

- Maximum 50 lines per AGENT.md
- No content duplication from CLAUDE.md -- only file path pointers
- No architecture explanations -- link to docs instead
- Include the scope disclaimer as the first blockquote
- May contain local paths meaningful only in developer environments

## Template

```markdown
# AGENT.md -- {repo_name}

> LLM navigation guide. Points to context sources -- does not duplicate them.

## Context

- **Architecture**: `{path}`
- **API reference**: `{path}`
- **Conventions**: `CLAUDE.md`

## Commands

- Tests: `{test_command}`
- Lint: `{lint_command}`
- Type check: `{typecheck_command}`
- Pre-commit: `pre-commit run --all-files`

## Cross-Repo

- Shared platform standards: `~/.claude/CLAUDE.md`

## Rules

- {repo-specific rules}
```
