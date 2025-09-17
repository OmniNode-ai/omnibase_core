#!/bin/bash

# Copy scripts directory to all 6 repositories
repos=(
    "../omnibase_spi"
    "../omniagent"
    "../omnibase_infra"
    "../omniplan"
    "../omnimcp"
    "../omnimemory"
)

echo "Copying scripts/ directory to all repositories..."

for repo in "${repos[@]}"; do
    if [ -d "$repo" ]; then
        echo "Copying scripts/ to $repo..."
        if [ -d "scripts" ]; then
            cp -r scripts "$repo/"
            echo "  ✓ Copied scripts/ directory"
        else
            echo "  ❌ scripts/ directory not found"
        fi
    else
        echo "❌ Repository $repo not found"
    fi
done

echo "Scripts copy completed!"
