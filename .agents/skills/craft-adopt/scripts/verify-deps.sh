#!/usr/bin/env bash
# Verify Craft setup: manifest, Addy core skills, Craft-native skills.
# Exit 0 = ready; exit 1 = fix instructions printed.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRAFT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MANIFEST="$CRAFT_ROOT/craft.manifest.yaml"
PROJECT_DIR="${1:-$(pwd)}"

expand_path() {
  local p="$1"
  p="${p/#\~/$HOME}"
  if [[ "$p" != /* ]]; then
    p="$(pwd)/$p"
  fi
  echo "$p"
}

build_search_paths() {
  SEARCH_PATHS=()
  if [[ -d "$PROJECT_DIR/.agents/skills" ]]; then
    SEARCH_PATHS+=("$(expand_path "$PROJECT_DIR/.agents/skills")")
  fi
  if [[ -d ".agents/skills" ]]; then
    SEARCH_PATHS+=("$(expand_path ".agents/skills")")
  fi
  if [[ -d "$HOME/.agents/skills" ]]; then
    SEARCH_PATHS+=("$(expand_path "$HOME/.agents/skills")")
  fi
}

skill_found() {
  local skill="$1"
  local base
  for base in "${SEARCH_PATHS[@]}"; do
    if [[ -f "$base/$skill/SKILL.md" ]]; then
      return 0
    fi
  done
  return 1
}

extract_skill_list() {
  local mode="$1"
  awk -v mode="$mode" '
    /id: addyosmani\/agent-skills/ { in_addy=1; next }
    in_addy && /^  - id:/ { in_addy=0 }
    in_addy && /^    skills:/ { in_req=1; in_opt=0; next }
    in_addy && /^    optional_skills:/ { in_req=0; in_opt=1; next }
    in_addy && in_req && mode=="required" && /^      - / { print substr($0, 9) }
    in_addy && in_opt && mode=="optional" && /^      - / { print substr($0, 9) }
    in_addy && /^    [a-z_]/ && !/^      - / { in_req=0; in_opt=0 }
  ' "$MANIFEST"
}

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: craft.manifest.yaml not found at:"
  echo "  $MANIFEST"
  echo ""
  echo "Clone Craft first:"
  echo "  git clone git@github.com:DTiapan/craft.git"
  exit 1
fi

build_search_paths

echo "Craft dependency check (reference-only)"
echo "Manifest: $MANIFEST"
echo "Target:   $PROJECT_DIR"
echo "Search paths:"
printf '  - %s\n' "${SEARCH_PATHS[@]}"
echo ""

missing=()
while IFS= read -r skill; do
  [[ -z "$skill" ]] && continue
  if ! skill_found "$skill"; then
    missing+=("$skill")
  fi
done < <(extract_skill_list required)

missing_craft=()
while IFS= read -r skill; do
  [[ -z "$skill" ]] && continue
  if [[ ! -f "$CRAFT_ROOT/skills/$skill/SKILL.md" ]]; then
    missing_craft+=("$skill")
  fi
done < <(awk '/^craft_native:/ { nc=1; next } nc && /^  - / { print substr($0, 5) }' "$MANIFEST")

optional_missing=()
while IFS= read -r skill; do
  [[ -z "$skill" ]] && continue
  if ! skill_found "$skill"; then
    optional_missing+=("$skill")
  fi
done < <(extract_skill_list optional)

failed=0

if ((${#missing_craft[@]})); then
  echo "ERROR: Craft repo is incomplete (missing native skills):"
  printf '  - %s\n' "${missing_craft[@]}"
  echo "  Re-clone Craft: git clone git@github.com:DTiapan/craft.git"
  failed=1
fi

if ((${#missing[@]})); then
  echo "ERROR: Missing required Addy skills (${#missing[@]}):"
  printf '  - %s\n' "${missing[@]}"
  echo ""
  echo "Fix (initialize in your project root):"
  echo "  bash $CRAFT_ROOT/scripts/craft-install.sh --profile all --project-dir $PROJECT_DIR"
  echo ""
  echo "Re-run:"
  echo "  bash $CRAFT_ROOT/skills/craft-adopt/scripts/verify-deps.sh $PROJECT_DIR"
  failed=1
fi

if (( failed )); then
  exit 1
fi

echo "OK: All required Addy core skills found."
echo "OK: Craft-native skills present in repo."

if ((${#optional_missing[@]})); then
  echo ""
  echo "Note: optional router skills not installed (${#optional_missing[@]}). Craft still works."
  echo "  Examples: implement, diagnose, domain-modeling, codebase-design"
fi

exit 0
