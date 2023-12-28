
SRCS := $(shell find src -name '*.py')
VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(PYTHON) -m pip
FIKL := $(VENV)/bin/fikl
PROTO_DEF_DIR := proto
PROTO_OUT_DIR := src/fikl/proto
PROTO_PY := $(PROTO_OUT_DIR)/config_pb2.py
PROTO_PYI := $(PROTO_OUT_DIR)/config_pb2.pyi
COVERAGE_SQLITE := .coverage.sqlite
COVERAGE_HTML := .coverage_html

# SRCS includes proto generated files, so there's no need for a separate rule for them
$(FIKL): pyproject.toml $(SRCS)
	@echo "Building fikl: $(FIKL)"
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install "setuptools>=62.0.0"
	$(PIP) install -e .

$(PROTO_PY) $(PROTO_PYI): proto/config.proto
	protoc \
		-I="$(PROTO_DEF_DIR)" \
		--python_out="$(PROTO_OUT_DIR)" \
		--pyi_out="$(PROTO_OUT_DIR)" \
		"$(PROTO_DEF_DIR)"/config.proto

.PHONY: lint
lint: $(FIKL)
	$(PYTHON) -m black --verbose src tests scripts --exclude $(PROTO_OUT_DIR)

.PHONY: test
test: $(FIKL)
	$(PYTHON) -m pytest

$(COVERAGE_SQLITE): $(FIKL)
	$(PYTHON) -m coverage run --source=src --data-file=$(COVERAGE_SQLITE) -m pytest 

$(COVERAGE_HTML): $(COVERAGE_SQLITE)
	$(PYTHON) -m coverage html --data-file=$(COVERAGE_SQLITE) -d $(COVERAGE_HTML)

.PHONY: coverage
coverage: $(COVERAGE_HTML)

.PHONY: mypy
mypy: $(FIKL)
	$(PYTHON) -m pytest --mypy

.PHONY: pyright
pyright: $(FIKL)
	$(PYTHON) -m pyright

.PHONY: clean
clean:
	git clean -ffdX
