
SRCS := $(shell find src -name '*.py')
VENV_NAME := .venv
PYTHON := $(VENV_NAME)/bin/python3
PIP := $(PYTHON) -m pip
FIKL := $(VEN_NAME)/bin/fikl
PROTO_DEF_DIR := proto
PROTO_OUT_DIR := src/fikl/proto
PROTO_PY := $(PROTO_OUT_DIR)/config_pb2.py
PROTO_PYI := $(PROTO_OUT_DIR)/config_pb2.pyi

# .PHONY: all install src lint test mypy pyright

.PHONY: all
all: install lint test coverage mypy pyright

# SRCS includes proto generated files
.PHONY: src
src: $(SRCS)

# TODO: ensure protobuf is installed
$(PROTO_PY) $(PROTO_PYI): proto/config.proto
	protoc \
		-I="$(PROTO_DEF_DIR)" \
		--python_out="$(PROTO_OUT_DIR)" \
		--pyi_out="$(PROTO_OUT_DIR)" \
		"$(PROTO_DEF_DIR)"/config.proto

$(FIKL): pyproject.toml proto src
	python3 -m venv $(VENV_NAME)
	$(PIP) install --upgrade pip
	$(PIP) install "setuptools>=62.0.0"
	$(PIP) install -e .

.PHONY: install
install: $(VENV_NAME)

.PHONY: lint
lint: $(VENV_NAME)
	$(PYTHON) -m black --verbose src tests scripts --exclude $(PROTO_OUT_DIR)

.PHONY: test
test: $(VENV_NAME)
	$(PYTHON) -m pytest

COVERAGE_SQLITE := coverage.sqlite
$(COVERAGE_SQLITE): $(VENV_NAME)
	$(PYTHON) -m coverage run --source=src --data-file=$(COVERAGE_SQLITE) -m pytest 

COVERAGE_HTML := coverage_html
$(COVERAGE_HTML): $(COVERAGE_SQLITE)
	$(PYTHON) -m coverage html --data-file=$(COVERAGE_SQLITE) -d $(COVERAGE_HTML)

.PHONY: coverage
coverage: $(COVERAGE_HTML)

# mypy: $(VENV_NAME)
# 	$(PYTHON) -m pytest --mypy

# pyright: $(VENV_NAME)
# 	$(PYTHON) -m pyright

# ipy: $(VENV_NAME)
# 	$(PYTHON) -m IPython

.PHONY: clean
clean:
	git clean -ffdX
