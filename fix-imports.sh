#!/bin/bash
# Automated import pattern fixes for ONEX codebase

# Fix models/config directory
echo "🔧 Fixing models/config directory (54 violations)..."
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/config

# Fix triple-dot imports to enums
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;

# Fix triple-dot imports to exceptions
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;

# Fix triple-dot imports to protocols_local
find . -name "*.py" -exec sed -i 's/from \.\.\.protocols_local\./from omnibase_core.protocols_local./g' {} \;

# Fix double-dot imports to other model directories
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.metadata\./from omnibase_core.models.metadata./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.infrastructure\./from omnibase_core.models.infrastructure./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.core\./from omnibase_core.models.core./g' {} \;

echo "✅ models/config directory fixed"

# Fix models/nodes directory
echo "🔧 Fixing models/nodes directory (108 violations)..."
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/nodes

# Fix triple-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.protocols_local\./from omnibase_core.protocols_local./g' {} \;

# Fix double-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.metadata\./from omnibase_core.models.metadata./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.infrastructure\./from omnibase_core.models.infrastructure./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.core\./from omnibase_core.models.core./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.connections\./from omnibase_core.models.connections./g' {} \;

echo "✅ models/nodes directory fixed"

# Fix models/cli directory
echo "🔧 Fixing models/cli directory (92 violations)..."
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/cli

# Fix triple-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;

# Fix double-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.metadata\./from omnibase_core.models.metadata./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.infrastructure\./from omnibase_core.models.infrastructure./g' {} \;

echo "✅ models/cli directory fixed"

# Fix models/metadata directory
echo "🔧 Fixing models/metadata directory (83 violations)..."
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/metadata

# Fix triple-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.utils\./from omnibase_core.utils./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.models\./from omnibase_core.models./g' {} \;

# Fix double-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.infrastructure\./from omnibase_core.models.infrastructure./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.nodes\./from omnibase_core.models.nodes./g' {} \;

echo "✅ models/metadata directory fixed"

# Fix models/core directory
echo "🔧 Fixing models/core directory (51 violations)..."
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/core

# Fix double-dot imports
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.infrastructure\./from omnibase_core.models.infrastructure./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.metadata\./from omnibase_core.models.metadata./g' {} \;

echo "✅ models/core directory fixed"

# Fix remaining smaller directories
echo "🔧 Fixing remaining directories..."

# models/connections (26 violations)
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/connections
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;

# models/infrastructure (46 violations)
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/infrastructure
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.metadata\./from omnibase_core.models.metadata./g' {} \;

# models/contracts (3 violations)
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/contracts
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.metadata\./from omnibase_core.models.metadata./g' {} \;

# models/validation (8 violations)
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/validation
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;

# models/common (24 violations)
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/common
find . -name "*.py" -exec sed -i 's/from \.\.\.enums\./from omnibase_core.enums./g' {} \;
find . -name "*.py" -exec sed -i 's/from \.\.\.exceptions\./from omnibase_core.exceptions./g' {} \;

# models/utils (1 violation)
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/utils
find . -name "*.py" -exec sed -i 's/from \.\.common\./from omnibase_core.models.common./g' {} \;

echo "✅ All directories processed!"
echo "🔍 Running validation to check results..."

# Return to root and run validation
cd /Volumes/PRO-G40/Code/omnibase_core
poetry run python scripts/validation/validate-import-patterns.py src/ --max-violations 0
