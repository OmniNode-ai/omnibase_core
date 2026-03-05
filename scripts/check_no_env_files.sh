#!/bin/bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Prevent .env file commits
# Enforces use of ~/.omnibase/.env as the single source of truth
# Blocks commits of .env files (except .env.example)

if git diff --cached --name-only | grep -E "(^|/)\\.env([._-].+)?\$" | grep -v "\\.env\\.example"; then
    echo "BLOCKED: .env file staged for commit"
    echo "Use ~/.omnibase/.env instead (from the single source of truth)"
    echo "To unstage: git reset HEAD <file>"
    exit 1
fi

exit 0
