
SRCS := $(shell find src -name '*.py')
VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(PYTHON) -m pip
FIKL := $(VEN_NAME)/bin/fikl
PROTO_DEF_DIR := proto
PROTO_OUT_DIR := src/fikl/proto
PROTO_PY := $(PROTO_OUT_DIR)/config_pb2.py
PROTO_PYI := $(PROTO_OUT_DIR)/config_pb2.pyi
COVERAGE_SQLITE := .coverage.sqlite
COVERAGE_HTML := .coverage_html

# .PHONY: all install src lint test mypy pyright

.PHONY: all
all: install lint test coverage mypy pyright

# SRCS includes proto generated files
.PHONY: srcs
srcs: $(SRCS)

# Rule to check if protoc is installed
.PHONY: ensure-protoc
ensure-protoc:
	@which protoc > /dev/null || (echo "protoc is not installed. Please install it." && false)

$(PROTO_PY) $(PROTO_PYI): proto/config.proto ensure-protoc
	protoc \
		-I="$(PROTO_DEF_DIR)" \
		--python_out="$(PROTO_OUT_DIR)" \
		--pyi_out="$(PROTO_OUT_DIR)" \
		"$(PROTO_DEF_DIR)"/config.proto

$(FIKL): pyproject.toml proto srcs
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install "setuptools>=62.0.0"
	$(PIP) install -e .

.PHONY: install
install: $(FIKL)

.PHONY: lint
lint: $(VENV)
	$(PYTHON) -m black --verbose src tests scripts --exclude $(PROTO_OUT_DIR)

.PHONY: test
test: $(VENV)
	$(PYTHON) -m pytest

$(COVERAGE_SQLITE): $(VENV)
	$(PYTHON) -m coverage run --source=src --data-file=$(COVERAGE_SQLITE) -m pytest 

$(COVERAGE_HTML): $(COVERAGE_SQLITE)
	$(PYTHON) -m coverage html --data-file=$(COVERAGE_SQLITE) -d $(COVERAGE_HTML)

.PHONY: coverage
coverage: $(COVERAGE_HTML)

mypy: $(VENV)
	$(PYTHON) -m pytest --mypy

pyright: $(VENV)
	$(PYTHON) -m pyright

.PHONY: clean
clean:
	git clean -ffdX
