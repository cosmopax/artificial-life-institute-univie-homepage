#!/bin/bash
set -euo pipefail

# Usage: ./tools/run_agent.sh [jules|codex|gemini|copilot]

AGENT=${1:-}
MD_DIR="agent_inputs"
CONTEXT_FILES=("PROJECT_CONTEXT.md" "ROADMAP.md" "CODING_STANDARDS.md")

if [[ -z "$AGENT" ]]; then
  echo "Usage: $0 [jules|codex|gemini|copilot]"
  exit 1
fi

INSTRUCTION_FILE="$MD_DIR/$AGENT.md"

if [[ ! -f "$INSTRUCTION_FILE" ]]; then
  echo "Error: Instruction file '$INSTRUCTION_FILE' not found."
  exit 1
fi

# Construct Global Context
FULL_PROMPT=""
echo "Loading global context..."
for file in "${CONTEXT_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    FULL_PROMPT+=$'\n\n'
    FULL_PROMPT+="--- CONTENT OF $file ---"
    FULL_PROMPT+=$'\n'
    FULL_PROMPT+=$(cat "$file")
  fi
done

# Read Status Board
STATUS_CONTEXT=""
if [[ -d "agent_state" ]]; then
  STATUS_CONTEXT+=$'\n\n--- CURRENT SQUAD STATUS ---\n'
  for status_file in agent_state/*.status; do
    if [[ -f "$status_file" ]]; then
        STATUS_CONTEXT+="[$(basename "$status_file" .status)]: $(cat "$status_file")\n"
    fi
  done
fi

# Add Specific Instructions
FULL_PROMPT+=$'\n\n'
FULL_PROMPT+="--- AGENT INSTRUCTIONS ---"
FULL_PROMPT+=$'\n'
FULL_PROMPT+=$(cat "$INSTRUCTION_FILE")
FULL_PROMPT+="$STATUS_CONTEXT"

# Synergy Instruction
FULL_PROMPT+=$'\n\n'
FULL_PROMPT+="[SYSTEM NOTICE]: You are part of a squad. Creating 'agent_state/$AGENT.status' with a one-line summary of your current action is encouraged."

echo "Launching $AGENT..."

case "$AGENT" in
  jules)
    # Jules accepts input via pipe for 'jules new'
    echo "$FULL_PROMPT" | jules new
    ;;
  codex)
    # Assuming 'codex' CLI accepts prompt via -p or arg. 
    # If it accepts stdin: echo "$FULL_PROMPT" | codex
    # Validating standard usage: codex "prompt"
    # We will pass it as an argument.
    codex "$FULL_PROMPT"
    ;;
  gemini)
    # Standard Gemini CLI usage
    gemini -p "$FULL_PROMPT"
    ;;
  copilot)
    # GitHub Copilot CLI - Force Prompt Output (CLI Deprecated/Unreliable)
    echo -e "\n---------------------------------------------------"
    echo "Please COPY the prompt below and PASTE it into your IDE Copilot Chat:"
    echo "---------------------------------------------------"
    echo "$FULL_PROMPT"
    echo "---------------------------------------------------"
    ;;
  *)
    echo "Unknown agent: $AGENT"
    exit 1
    ;;
esac
