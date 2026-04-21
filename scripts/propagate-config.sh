#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# OMN-9344: cross-repo config propagator bot.
#
# Invoked by .github/workflows/propagate-config.yml on release-tag events.
# Reads .github/propagation-targets.yaml and, for the propagation named by
# $PROPAGATION_NAME, opens one PR per target repo adding the declared
# config entry (currently only operation=append_hook_entry on
# .pre-commit-config.yaml).
#
# Scope: MINIMAL. One operation type. One trigger. Extensibility lives in
# the yaml targets, not in this script's conditional tree.
#
# Required env:
#   PROPAGATION_NAME            name of the propagation entry to execute
#   GITHUB_TOKEN                gh auth for cross-repo PR creation
# Optional env:
#   PROPAGATION_TARGETS_FILE    default: .github/propagation-targets.yaml
#   PROPAGATION_DRY_RUN         "1" prints DRY_RUN: gh ... lines instead of
#                               invoking gh. Used by the pytest harness.
#   PROPAGATION_RELEASE_TAG     injected into PR body for traceability.
#
# Idempotency: if the target .pre-commit-config.yaml already references the
# declared hook_id, the script skips that repo (no duplicate PR).

set -euo pipefail

: "${PROPAGATION_NAME:?PROPAGATION_NAME must be set (e.g. normalization-symmetry-hook)}"
: "${GITHUB_TOKEN:?GITHUB_TOKEN must be set}"

TARGETS_FILE="${PROPAGATION_TARGETS_FILE:-.github/propagation-targets.yaml}"
DRY_RUN="${PROPAGATION_DRY_RUN:-0}"
RELEASE_TAG="${PROPAGATION_RELEASE_TAG:-unknown}"

if [[ ! -f "$TARGETS_FILE" ]]; then
  echo "ERROR: targets file not found: $TARGETS_FILE" >&2
  exit 2
fi

# Emit targets for the selected propagation as JSON lines so bash can loop
# over them without a second yaml dependency. Also enforces that the
# propagation name exists and the operation is supported.
emit_targets() {
  python3 - "$TARGETS_FILE" "$PROPAGATION_NAME" <<'PY'
import json, sys, pathlib
try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: pyyaml required (pip install pyyaml)\n")
    sys.exit(2)

path = pathlib.Path(sys.argv[1])
name = sys.argv[2]
data = yaml.safe_load(path.read_text()) or {}
props = data.get("propagations") or []
match = next((p for p in props if p.get("name") == name), None)
if match is None:
    sys.stderr.write(f"ERROR: propagation '{name}' not found in {path}\n")
    sys.exit(3)

supported_ops = {"append_hook_entry"}
supported_merge_methods = {"queue_default", "squash", "merge", "rebase"}
merge_method = match.get("merge_method", "queue_default")
if merge_method not in supported_merge_methods:
    sys.stderr.write(
        f"ERROR: unsupported merge_method '{merge_method}' "
        f"(supported: {sorted(supported_merge_methods)})\n"
    )
    sys.exit(5)

for target in match.get("targets") or []:
    op = target.get("operation")
    if op not in supported_ops:
        sys.stderr.write(f"ERROR: unsupported operation '{op}' (supported: {sorted(supported_ops)})\n")
        sys.exit(4)

print(json.dumps({
    "auto_merge": bool(match.get("auto_merge", False)),
    "merge_method": merge_method,
    "targets": match.get("targets") or [],
}))
PY
}

PROPAGATION_JSON="$(emit_targets)"

AUTO_MERGE="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["auto_merge"])' "$PROPAGATION_JSON")"
MERGE_METHOD="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["merge_method"])' "$PROPAGATION_JSON")"
TARGET_COUNT="$(python3 -c 'import json,sys;print(len(json.loads(sys.argv[1])["targets"]))' "$PROPAGATION_JSON")"

echo "Propagation: $PROPAGATION_NAME"
echo "Targets: $TARGET_COUNT"
echo "Auto-merge: $AUTO_MERGE (method=$MERGE_METHOD)"

BRANCH="bot/propagate-${PROPAGATION_NAME}-${RELEASE_TAG}"

for i in $(seq 0 $((TARGET_COUNT - 1))); do
  REPO="$(python3 -c 'import json,sys,os;print(json.loads(sys.argv[1])["targets"][int(os.environ["IDX"])]["repo"])' "$PROPAGATION_JSON" IDX="$i" 2>/dev/null \
    || python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.loads(sys.argv[1])["targets"][i]["repo"])' "$PROPAGATION_JSON" "$i")"
  FILE_PATH="$(python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.loads(sys.argv[1])["targets"][i]["path"])' "$PROPAGATION_JSON" "$i")"
  HOOK_ID="$(python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.loads(sys.argv[1])["targets"][i]["hook_id"])' "$PROPAGATION_JSON" "$i")"

  TITLE="chore(ci): propagate ${PROPAGATION_NAME} to ${FILE_PATH} [bot] [OMN-9344]"
  BODY=$(cat <<EOF
Automated config propagation emitted by \`omnibase_core/propagate-config.yml\`.

- Propagation: \`${PROPAGATION_NAME}\`
- Hook ID: \`${HOOK_ID}\`
- Release tag: \`${RELEASE_TAG}\`
- Source: https://github.com/OmniNode-ai/omnibase_core/releases/tag/${RELEASE_TAG}
- Tracking: OMN-9344

Idempotent — if the hook already exists in \`${FILE_PATH}\`, the bot skips this repo.
EOF
)

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN: gh pr list --repo ${REPO} --state open --search \"propagate ${PROPAGATION_NAME}\" (dedup check)"
    echo "DRY_RUN: gh pr create --repo ${REPO} --head ${BRANCH} --base main --title \"${TITLE}\""
    if [[ "$AUTO_MERGE" == "True" || "$AUTO_MERGE" == "true" ]]; then
      # Per OMN-8838: always arm auto-merge via GraphQL enablePullRequestAutoMerge
      # (never `gh pr merge --auto` — it silently picks the wrong method).
      echo "DRY_RUN: gh api graphql enablePullRequestAutoMerge(mergeMethod: SQUASH) --auto ${REPO}#<pr>"
    fi
    continue
  fi

  # Live path (executed inside GitHub Actions runner with gh + git configured).

  # Dedup: refuse to create a second PR if one is already open for this branch.
  # Uses exit-status check instead of || true to surface auth/API failures.
  if ! EXISTING_PR="$(gh pr list --repo "$REPO" --state open \
    --search "propagate ${PROPAGATION_NAME}" --json number,headRefName \
    --jq "[.[] | select(.headRefName | startswith(\"bot/propagate-${PROPAGATION_NAME}-\"))] | first | .number" 2>/dev/null)"; then
    echo "ERROR: dedup check failed for ${REPO}; refusing to proceed blindly" >&2
    continue
  fi
  if [[ -n "$EXISTING_PR" && "$EXISTING_PR" != "null" ]]; then
    echo "SKIP: ${REPO} already has open PR #${EXISTING_PR} for branch ${BRANCH}"
    continue
  fi

  TMPDIR="$(mktemp -d)"
  trap "rm -rf $TMPDIR" EXIT
  pushd "$TMPDIR" >/dev/null

  # gh repo clone uses GITHUB_TOKEN for the initial clone, but subsequent
  # git push requires git credentials configured separately.
  gh auth setup-git
  gh repo clone "$REPO" downstream -- --depth=5
  cd downstream

  # Dedup: skip if an open bot PR for this propagation already exists. Each
  # workflow_dispatch gets a unique manual-<run_id> tag, so without this check
  # every re-run opens a fresh PR even though the previous one is still open.
  EXISTING_PR="$(gh pr list --repo "$REPO" --state open \
    --search "propagate ${PROPAGATION_NAME}" --json number,headRefName \
    --jq "[.[] | select(.headRefName | startswith(\"bot/propagate-${PROPAGATION_NAME}-\"))] | first | .number" 2>/dev/null || true)"
  if [[ -n "$EXISTING_PR" && "$EXISTING_PR" != "null" ]]; then
    echo "SKIP: ${REPO} already has open PR #${EXISTING_PR} for propagation ${PROPAGATION_NAME}"
    popd >/dev/null
    rm -rf "$TMPDIR"
    trap - EXIT
    continue
  fi

  if [[ ! -f "$FILE_PATH" ]]; then
    echo "ERROR: ${REPO} is missing ${FILE_PATH} — skipping to avoid creating invalid config" >&2
    popd >/dev/null
    rm -rf "$TMPDIR"
    trap - EXIT
    continue
  fi

  if grep -q "id:\s*${HOOK_ID}" "$FILE_PATH" 2>/dev/null; then
    echo "SKIP: ${REPO} already contains hook ${HOOK_ID} in ${FILE_PATH}"
    popd >/dev/null
    rm -rf "$TMPDIR"
    trap - EXIT
    continue
  fi

  # Append hook block. The exact snippet lives in the source repo so the
  # script stays minimal; shell here just wires it up.
  APPEND_SNIPPET="$(cat <<SNIPPET
  - repo: local
    hooks:
      - id: ${HOOK_ID}
        name: ${HOOK_ID}
        entry: uv run python -m omnibase_core.validators.${HOOK_ID}
        language: system
        pass_filenames: false
SNIPPET
)"
  printf '\n%s\n' "$APPEND_SNIPPET" >> "$FILE_PATH"

  git config user.name "onex-propagate-bot"
  git config user.email "bot@omninode.ai"
  git checkout -b "$BRANCH"
  git add "$FILE_PATH"
  git commit -m "chore(ci): propagate ${PROPAGATION_NAME} [bot]"
  git push -u origin "$BRANCH" --force-with-lease

  PR_URL="$(gh pr create --repo "$REPO" --head "$BRANCH" --base main \
    --title "$TITLE" --body "$BODY")"
  echo "Created: $PR_URL"

  if [[ "$AUTO_MERGE" == "True" || "$AUTO_MERGE" == "true" ]]; then
    PR_NUMBER="$(echo "$PR_URL" | sed -E 's#.*/pull/([0-9]+).*#\1#')"
    # Per OMN-8838 + memory reference_github_merge_queue_api: always arm
    # auto-merge via GraphQL enablePullRequestAutoMerge with explicit
    # mergeMethod. `gh pr merge --auto` silently picks the wrong method on
    # merge-queue-enabled repos.
    case "$MERGE_METHOD" in
      queue_default|squash) GRAPHQL_METHOD="SQUASH" ;;
      merge) GRAPHQL_METHOD="MERGE" ;;
      rebase) GRAPHQL_METHOD="REBASE" ;;
      *) echo "ERROR: unknown merge_method '$MERGE_METHOD'" >&2; exit 5 ;;
    esac
    PR_ID="$(gh api "repos/${REPO}/pulls/${PR_NUMBER}" --jq '.node_id')"
    gh api graphql \
      -f query='mutation($id:ID!,$m:PullRequestMergeMethod!){enablePullRequestAutoMerge(input:{pullRequestId:$id,mergeMethod:$m}){pullRequest{number}}}' \
      -f id="$PR_ID" -f m="$GRAPHQL_METHOD"
  fi

  popd >/dev/null
  rm -rf "$TMPDIR"
  trap - EXIT
done

echo "Propagation complete: $PROPAGATION_NAME -> $TARGET_COUNT target(s)"
