
VENV_NAME := .venv
PYTHON := $(VENV_NAME)/bin/python3
PIP := $(PYTHON) -m pip

.PHONY: all install lint test coverage mypy pyright

all: install lint test coverage mypy pyright

install: $(VENV_NAME)

$(VENV_NAME): pyproject.toml
	python3 -m venv $(VENV_NAME)
	$(PIP) install setuptools>=62.0.0
	$(PIP) install -e .

lint: $(VENV_NAME)
	$(PYTHON) -m black .

test: $(VENV_NAME)
	$(PYTHON) -m pytest

coverage: $(VENV_NAME)
	$(PYTHON) -m coverage run --source=$REPO_DIR/src -m pytest 
	$(PYTHON) -m coverage html

mypy: $(VENV_NAME)
	$(PYTHON) -m pytest --mypy

pyright: $(VENV_NAME)
	$(PYTHON) -m pyright

ipy: $(VENV_NAME)
	$(PYTHON) -m IPython

clean:
	deactivate
	git clean -ffdX
