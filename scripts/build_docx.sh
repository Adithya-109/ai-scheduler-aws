#!/usr/bin/env bash
# Rebuild the journal .docx from RESEARCH_PAPER.md (needs pandoc).
set -euo pipefail
cd "$(dirname "$0")/.."
pandoc RESEARCH_PAPER.md -f markdown+tex_math_dollars -t docx -o AI_Scheduler_Journal_Paper.docx
echo "wrote AI_Scheduler_Journal_Paper.docx"
