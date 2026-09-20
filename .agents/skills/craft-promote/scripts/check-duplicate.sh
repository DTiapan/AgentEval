#!/usr/bin/env bash
# Check if a proposed skill name/description duplicates existing installed skills.
set -euo pipefail

QUERY="${1:-}"
if [[ -z "$QUERY" ]]; then
  echo "Usage: $0 <search-term-or-skill-name>"
  exit 2
fi

search_paths=(
  ".agents/skills"
  "${HOME}/.agents/skills"
)

echo "Searching for duplicates matching: $QUERY"
echo ""

for base in "${search_paths[@]}"; do
  [[ -d "$base" ]] || continue
  while IFS= read -r skill_md; do
    dir="$(dirname "$skill_md")"
    name="$(basename "$dir")"
    if grep -qi "$QUERY" "$skill_md" 2>/dev/null || [[ "$name" == *"$QUERY"* ]]; then
      echo "  [$name] $skill_md"
      head -5 "$skill_md" | grep -E '^name:|^description:' || true
      echo ""
    fi
  done < <(find "$base" -name SKILL.md 2>/dev/null)
done
