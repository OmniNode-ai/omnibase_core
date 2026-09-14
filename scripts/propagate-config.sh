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

source = match.get("source")
if not isinstance(source, str) or not source:
    sys.stderr.write(f"ERROR: propagation '{name}' must declare a source file\n")
    sys.exit(6)
source_path = pathlib.Path(source)
if not source_path.is_file():
    sys.stderr.write(f"ERROR: propagation source not found: {source}\n")
    sys.exit(6)
source_hooks = yaml.safe_load(source_path.read_text()) or []
if not isinstance(source_hooks, list):
    sys.stderr.write(f"ERROR: propagation source must contain a hook list: {source}\n")
    sys.exit(6)

tracking_issue = match.get("tracking_issue")
if not isinstance(tracking_issue, str) or not tracking_issue:
    sys.stderr.write(f"ERROR: propagation '{name}' must declare tracking_issue\n")
    sys.exit(7)

targets = []
for target in match.get("targets") or []:
    op = target.get("operation")
    if op not in supported_ops:
        sys.stderr.write(f"ERROR: unsupported operation '{op}' (supported: {sorted(supported_ops)})\n")
        sys.exit(4)
    hook_id = target.get("hook_id")
    hook = next(
        (candidate for candidate in source_hooks if candidate.get("id") == hook_id),
        None,
    )
    if hook is None:
        sys.stderr.write(
            f"ERROR: hook '{hook_id}' is not declared in propagation source {source}\n"
        )
        sys.exit(8)
    targets.append({**target, "hook": hook})

print(json.dumps({
    "auto_merge": bool(match.get("auto_merge", False)),
    "merge_method": merge_method,
    "source": source,
    "tracking_issue": tracking_issue,
    "targets": targets,
}))
PY
}

PROPAGATION_JSON="$(emit_targets)"

AUTO_MERGE="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["auto_merge"])' "$PROPAGATION_JSON")"
MERGE_METHOD="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["merge_method"])' "$PROPAGATION_JSON")"
TARGET_COUNT="$(python3 -c 'import json,sys;print(len(json.loads(sys.argv[1])["targets"]))' "$PROPAGATION_JSON")"
SOURCE_FILE="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["source"])' "$PROPAGATION_JSON")"
TRACKING_ISSUE="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["tracking_issue"])' "$PROPAGATION_JSON")"

echo "Propagation: $PROPAGATION_NAME"
echo "Targets: $TARGET_COUNT"
echo "Auto-merge: $AUTO_MERGE (method=$MERGE_METHOD)"

BRANCH="bot/propagate-${PROPAGATION_NAME}-${RELEASE_TAG}"

resolve_default_branch() {
  local repo="$1"
  local branch
  if ! branch="$(gh api "repos/${repo}" --jq '.default_branch' 2>/dev/null)"; then
    echo "ERROR: failed to resolve default branch for ${repo}; refusing to proceed" >&2
    return 1
  fi
  if [[ -z "$branch" || "$branch" == "null" ]]; then
    echo "ERROR: empty default branch for ${repo}; refusing to proceed" >&2
    return 1
  fi
  printf '%s\n' "$branch"
}

for i in $(seq 0 $((TARGET_COUNT - 1))); do
  REPO="$(python3 -c 'import json,sys,os;print(json.loads(sys.argv[1])["targets"][int(os.environ["IDX"])]["repo"])' "$PROPAGATION_JSON" IDX="$i" 2>/dev/null \
    || python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.loads(sys.argv[1])["targets"][i]["repo"])' "$PROPAGATION_JSON" "$i")"
  FILE_PATH="$(python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.loads(sys.argv[1])["targets"][i]["path"])' "$PROPAGATION_JSON" "$i")"
  HOOK_ID="$(python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.loads(sys.argv[1])["targets"][i]["hook_id"])' "$PROPAGATION_JSON" "$i")"
  HOOK_JSON="$(python3 -c 'import json,sys;i=int(sys.argv[2]);print(json.dumps(json.loads(sys.argv[1])["targets"][i]["hook"]))' "$PROPAGATION_JSON" "$i")"
  DEFAULT_BRANCH="$(resolve_default_branch "$REPO")"

  APPEND_SNIPPET="$(python3 -c 'import json,sys,yaml; print(yaml.safe_dump([{"repo": "local", "hooks": [json.loads(sys.argv[1])]}], sort_keys=False).rstrip())' "$HOOK_JSON")"

  TITLE="chore(ci): propagate ${PROPAGATION_NAME} to ${FILE_PATH} [bot] [${TRACKING_ISSUE}]"
  BODY=$(cat <<EOF
Automated config propagation emitted by \`omnibase_core/propagate-config.yml\`.

- Propagation: \`${PROPAGATION_NAME}\`
- Hook ID: \`${HOOK_ID}\`
- Release tag: \`${RELEASE_TAG}\`
- Source: https://github.com/OmniNode-ai/omnibase_core/releases/tag/${RELEASE_TAG}
- Tracking: ${TRACKING_ISSUE}

Idempotent — if the hook already exists in \`${FILE_PATH}\`, the bot skips this repo.
EOF
)

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN: gh pr list --repo ${REPO} --state open --search \"propagate ${PROPAGATION_NAME}\" (dedup check)"
    echo "DRY_RUN: append canonical hook ${HOOK_ID} from ${SOURCE_FILE} to ${REPO}:${FILE_PATH}"
    printf '%s\n' "$APPEND_SNIPPET"
    echo "DRY_RUN: gh pr create --repo ${REPO} --head ${BRANCH} --base ${DEFAULT_BRANCH} --title \"${TITLE}\""
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
  gh repo clone "$REPO" downstream -- --depth=5 --branch "$DEFAULT_BRANCH"
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

  # Append the exact canonical hook mapping loaded from the declared source.
  # The shell only wraps it as a local-repo pre-commit entry.
  printf '\n%s\n' "$APPEND_SNIPPET" >> "$FILE_PATH"

  git config user.name "onex-propagate-bot"
  git config user.email "bot@omninode.ai"
  git checkout -b "$BRANCH"
  git add "$FILE_PATH"
  git commit -m "chore(ci): propagate ${PROPAGATION_NAME} [bot]"
  git push -u origin "$BRANCH" --force-with-lease

  PR_URL="$(gh pr create --repo "$REPO" --head "$BRANCH" --base "$DEFAULT_BRANCH" \
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
