#!/bin/bash
# Сравнивает два локальных скриншота.
#
# Usage:
#   bash .claude/skills/screenshot-compare/scripts/screenshots-compare.sh <скриншот_a> <скриншот_b>
#
# Example:
#   bash .claude/skills/screenshot-compare/scripts/screenshots-compare.sh screenshots/before.png screenshots/after.png

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node "$SCRIPT_DIR/../screenshots-compare.mjs" "$1" "$2"
