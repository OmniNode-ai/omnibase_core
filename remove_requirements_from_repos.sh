#!/bin/bash

# Remove requirements.txt from scripts/validation/ in all repositories
repos=(
    "../omnibase_spi"
    "../omniagent"
    "../omnibase_infra"
    "../omniplan"
    "../omnimcp"
    "../omnimemory"
)

echo "Removing requirements.txt from all repositories..."

for repo in "${repos[@]}"; do
    if [ -d "$repo" ]; then
        if [ -f "$repo/scripts/validation/requirements.txt" ]; then
            rm "$repo/scripts/validation/requirements.txt"
            echo "  ✓ Removed requirements.txt from $repo"
        else
            echo "  - No requirements.txt found in $repo"
        fi
    else
        echo "❌ Repository $repo not found"
    fi
done

echo "Requirements cleanup completed!"
