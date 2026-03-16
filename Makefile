# Root command entrypoints that operationalize Codex skills for SolarShare.

.PHONY: skill-audit skill-bug-hunt skill-fullstack skill-pdf skill-fitgpt-check skill-help

skill-audit:
	./scripts/skill-suite.sh audit

skill-bug-hunt:
	./scripts/skill-suite.sh bug-hunt

skill-fullstack:
	./scripts/skill-suite.sh fullstack

skill-pdf:
	@echo "Usage: make skill-pdf PDF=/absolute/or/relative/path/to/file.pdf"
	@if [ -z "$(PDF)" ]; then exit 1; fi
	./scripts/skill-suite.sh pdf "$(PDF)"

skill-fitgpt-check:
	./scripts/skill-suite.sh fitgpt-check

skill-help:
	./scripts/skill-suite.sh skills-help
