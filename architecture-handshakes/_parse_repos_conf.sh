#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Shared repos.conf parser — sourced by install.sh and check-policy-gate.sh.
# Outputs one repo name per line to stdout.
#
# Usage (bash 3.2+ compatible):
#   source "${SCRIPT_DIR}/_parse_repos_conf.sh"
#   MY_ARRAY=()
#   while IFS= read -r line; do MY_ARRAY+=("${line}"); done < <(parse_repos_conf "${REPOS_CONF}")
#
# Strips comments, leading/trailing whitespace, and blank lines.
# NOTE: Called via process substitution, so `exit` only terminates the subshell.
# Callers MUST guard for an empty result array after the while-read loop.

parse_repos_conf() {
    local conf_file="$1"

    if [[ ! -f "${conf_file}" ]]; then
        echo "ERROR: repos.conf not found at ${conf_file}" >&2
        return 2
    fi

    local output
    output=$(sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//' "${conf_file}" | grep -v '^$' || true)

    if [[ -z "${output}" ]]; then
        echo "ERROR: repos.conf contains no repo entries" >&2
        return 2
    fi

    printf '%s\n' "${output}"
}
