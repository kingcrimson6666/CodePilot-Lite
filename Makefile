.PHONY: install test run

install:
	pip install -e .

test:
	pytest

run:
	python -m src.app.cli run --task "summarize repository status"
