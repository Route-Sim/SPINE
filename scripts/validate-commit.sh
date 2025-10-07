#!/bin/bash
# Validates commit message format
# Usage: ./scripts/validate-commit.sh <commit-message>

commit_msg="$1"

# Conventional commit types
types="feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"

# Regex pattern for conventional commits
pattern="^($types)(\([a-z-]+\))?!?: .{1,100}$"

if ! echo "$commit_msg" | head -n 1 | grep -qE "$pattern"; then
    cat <<EOF
❌ Invalid commit message format!

Your commit message must follow the Conventional Commits specification:

Format: <type>[optional scope]: <description>

Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

Examples:
  ✅ feat: add vehicle telemetry tracking
  ✅ fix: correct route calculation bug
  ✅ feat(agents): add new vehicle type
  ✅ feat!: breaking change to API

Your message:
  ❌ $commit_msg

For more information, see: https://www.conventionalcommits.org/

EOF
    exit 1
fi

echo "✅ Commit message is valid"
exit 0
