#!/usr/bin/env bash
# Shared repos.conf parser — sourced by install.sh and check-policy-gate.sh.
# Outputs one repo name per line to stdout.
#
# Usage (bash 3.2+ compatible):
#   source "${SCRIPT_DIR}/_parse_repos_conf.sh"
#   MY_ARRAY=()
#   while IFS= read -r line; do MY_ARRAY+=("${line}"); done < <(parse_repos_conf "${REPOS_CONF}")
#
# Strips comments, leading/trailing whitespace, and blank lines.
# Exits with code 2 if the file is missing or contains no entries.

parse_repos_conf() {
    local conf_file="$1"

    if [[ ! -f "${conf_file}" ]]; then
        echo "ERROR: repos.conf not found at ${conf_file}" >&2
        exit 2
    fi

    local output
    output=$(sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//' "${conf_file}" | grep -v '^$')

    if [[ -z "${output}" ]]; then
        echo "ERROR: repos.conf contains no repo entries" >&2
        exit 2
    fi

    printf '%s\n' "${output}"
}
