SolarShare Codex Skills Integration

Purpose
- This repository includes a unified workflow so each Codex skill can be applied with concrete commands.

Integrated Skills
- `codebase-auditor`: repository health and contract checks.
- `bug-hunter`: focused regression and edge-case verification.
- `senior-fullstack-engineer`: end-to-end full workflow run.
- `pdf`: requirements/document extraction for deck-driven product work.
- `fitgpt-stack-engineer`: readiness check for future Android client integration.
- `skill-creator`: documented as the path for creating/updating custom skills in `~/.codex/skills`.
- `skill-installer`: documented as the path for listing/installing external skills into `~/.codex/skills`.

Command Surface
- `make skill-audit`
- `make skill-bug-hunt`
- `make skill-fullstack`
- `make skill-pdf PDF=/path/to/file.pdf`
- `make skill-fitgpt-check`
- `make skill-help`

Direct Script Surface
- `./scripts/skill-suite.sh audit`
- `./scripts/skill-suite.sh bug-hunt`
- `./scripts/skill-suite.sh fullstack`
- `./scripts/skill-suite.sh pdf /path/to/file.pdf`
- `./scripts/skill-suite.sh fitgpt-check`
- `./scripts/skill-suite.sh skills-help`

Notes
- The current repository is FastAPI + hosted static web frontend.
- `fitgpt-stack-engineer` checks are in readiness mode until Android modules are added.
- `skill-creator` and `skill-installer` are Codex environment operations, not runtime web-app code.
