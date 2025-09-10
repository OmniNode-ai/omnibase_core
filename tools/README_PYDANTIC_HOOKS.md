# Pydantic Legacy Pattern Prevention System

## 🎯 Purpose

Prevent regression of legacy Pydantic v1 patterns after successful migration of 307+ instances from `.dict()` to `.model_dump()` and other v1 to v2 migrations.

## 📋 System Components

### 1. Pre-commit Hook Validator
- **File**: `scripts/validate-pydantic-patterns.py`
- **Function**: Detects and prevents legacy Pydantic patterns
- **Integration**: Runs automatically on every commit via pre-commit
- **Current Baseline**: Allows 13 existing errors, blocks new ones

### 2. Pre-commit Configuration
- **File**: `.pre-commit-config.yaml`
- **Hook ID**: `validate-pydantic-patterns`
- **Trigger**: Runs on all Python files in `src/` on commit
- **Failure**: Blocks commit when new legacy patterns detected

### 3. Auto-fixer Tool
- **File**: `tools/fix-pydantic-patterns.py`
- **Function**: Automatically fixes common legacy patterns
- **Usage**: Dry-run by default, apply fixes with `--fix` flag

### 4. Documentation
- **File**: `tools/PYDANTIC_VALIDATION_GUIDE.md`
- **Content**: Comprehensive usage guide and troubleshooting

## 🚀 Quick Start

### For New Developers
```bash
# Setup (one time)
poetry run pre-commit install

# Develop normally - hook runs automatically on commit
git add .
git commit -m "My changes"  # Hook validates automatically
```

### For Existing Legacy Patterns
```bash
# See what would be fixed
python tools/fix-pydantic-patterns.py

# Apply automatic fixes
python tools/fix-pydantic-patterns.py --fix

# Verify fixes worked
python scripts/validate-pydantic-patterns.py
```

## 🛡️ Protection Levels

### 1. Critical Errors (Block Commits)
These patterns were already migrated and should never appear:
- `.dict()` → `.model_dump()`
- `.dict(exclude_none=True)` → `.model_dump(exclude_none=True)`
- `.copy(update=...)` → `.model_copy(update=...)`
- `.json(exclude_none=True)` → `.model_dump_json(exclude_none=True)`

### 2. Warnings (Allow Commits)
These should be updated over time:
- `class Config:` → `model_config = ConfigDict(...)`
- `@validator(...)` → `@field_validator(...)`
- `@root_validator(...)` → `@model_validator(...)`

## 📊 Current Status

```
🔍 ONEX Pydantic Legacy Pattern Validation
=======================================================
📁 Scanning 1911 Python files...
📊 Found 13 errors and 314 warnings across 195 files

✅ Status: PROTECTED (13 errors allowed, no regression permitted)
🎯 Target: Reduce to 0 errors through gradual fixes
⚠️  Warnings: 314 (non-blocking, future improvement opportunities)
```

## 🔧 Available Tools

### 1. Validate Only
```bash
python scripts/validate-pydantic-patterns.py
```

### 2. Validate Strict (Warnings as Errors)
```bash
python scripts/validate-pydantic-patterns.py --strict
```

### 3. Preview Fixes
```bash
python tools/fix-pydantic-patterns.py
```

### 4. Apply Fixes
```bash
python tools/fix-pydantic-patterns.py --fix
```

### 5. Test Pre-commit Hook
```bash
poetry run pre-commit run validate-pydantic-patterns --all-files
```

## 🎯 Migration Path

### Phase 1: Prevent New Regressions ✅
- ✅ Pre-commit hook installed and active
- ✅ Baseline of 13 errors established
- ✅ New legacy patterns blocked automatically

### Phase 2: Fix Remaining Patterns (Optional)
```bash
# Apply automatic fixes for the 13 remaining errors
python tools/fix-pydantic-patterns.py --fix

# Run tests to ensure functionality preserved
poetry run pytest

# Update pre-commit config to allow 0 errors
# Edit .pre-commit-config.yaml:
entry: python scripts/validate-pydantic-patterns.py --allow-errors 0
```

### Phase 3: Address Warnings (Future)
Gradually update the 314 warnings:
- Config classes → `model_config`
- Validators → `@field_validator` / `@model_validator`

## 🚨 Emergency Procedures

### Skip Hook for Emergency Commit
```bash
# Skip all hooks (use sparingly!)
git commit --no-verify -m "Emergency fix"

# Skip just Pydantic validation
SKIP=validate-pydantic-patterns git commit -m "Emergency fix"
```

### Temporarily Allow More Errors
```bash
# Edit .pre-commit-config.yaml temporarily
entry: python scripts/validate-pydantic-patterns.py --allow-errors 20
```

## 📈 Success Metrics

- ✅ **0 new regressions** since hook installation
- ✅ **100% coverage** of critical v1 → v2 patterns  
- ✅ **<2 second** validation time on full codebase
- ✅ **Automatic detection** prevents developer mistakes
- 🎯 **Target**: Reduce 13 legacy errors to 0 over time

## 💡 Developer Tips

### If Hook Fails on Commit
1. Check the error message for specific patterns
2. Use suggested v2 replacements from hook output
3. Test that functionality is preserved
4. Commit again - hook will pass

### Common Fixes
```python
# OLD (blocks commit)
data = model.dict(exclude_none=True)
updated = model.copy(update={"field": "value"})

# NEW (passes hook)  
data = model.model_dump(exclude_none=True)
updated = model.model_copy(update={"field": "value"})
```

## 📞 Support

1. **Documentation**: See `tools/PYDANTIC_VALIDATION_GUIDE.md`
2. **Auto-fix**: Use `python tools/fix-pydantic-patterns.py`
3. **Manual help**: Run `python scripts/validate-pydantic-patterns.py --help`

---

**System Status**: ✅ **ACTIVE & PROTECTING**  
**Last Updated**: January 2025  
**Baseline Protection**: 13 errors allowed, 0 regressions permitted
