# AGENTS.md - Local Instructions

## Mission
- Ship minimal, correct, reversible changes for the Artificial Life Institute homepage.

## Required reading (nearest wins)
- If this file is updated with links to project docs, read them first.

## Safety
- Operate only inside `/Users/cosmopax/Desktop/projx/artificial-life-institute-univie-homepage` and `/Users/cosmopax/WebspaceMount/artificiat27/html`.
- Before multi-file edits, take a checkpoint commit: `git add -A && git commit -m "checkpoint: pre-agent-edit"`.
- Quarantine existing webroot contents before deploy using `deploy.sh`.
- Do not expose secrets or environment dumps.

## Build + Deploy
- Build with `python3 tools/build.py`.
- Deploy with `./deploy.sh`.

## Logging
- Append one line to `LOG.md` per completed turn using:
  `ISO8601 | agent=codex | tags=... | summary | tests=...`
