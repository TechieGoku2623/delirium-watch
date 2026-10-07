export PATH := $(HOME)/.local/bin:$(PATH)
UV ?= uv

.PHONY: demo-shots setup lint test research eval demo demo-data record

setup:
	$(UV) sync --extra dev

lint:
	$(UV) run ruff check src tests research
	$(UV) run ruff format --check src tests research
	$(UV) run mypy

test:
	$(UV) run pytest

research:
	$(UV) run python research/phase0/run_all.py
	$(UV) run python research/phase3/eval/run.py
	$(UV) run python research/phase0/render_docs.py

eval:
	$(UV) run python research/phase0/label_agreement/run.py
	$(UV) run python research/phase0/base_rate/run.py
	$(UV) run python research/phase0/leakage_audit/run.py
	$(UV) run python research/phase3/eval/run.py
	$(UV) run python research/phase0/render_docs.py

demo:
	$(UV) run delirium-watch demo

demo-data:
	$(UV) run delirium-watch demo-data

demo-shots:
	$(UV) run --with pyyaml python demo/verify_shots.py

record:
	bash demo/record.sh
	bash demo/render.sh
