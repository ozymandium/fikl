
VENV_NAME := .venv
PYTHON := $(VENV_NAME)/bin/python3
PIP := $(PYTHON) -m pip
PROTO_DEF_DIR := proto
PROTO_OUT_DIR := src/fikl/proto
PROTO_PY := $(PROTO_OUT_DIR)/config_pb2.py
PROTO_PYI := $(PROTO_OUT_DIR)/config_pb2.pyi

.PHONY: all install proto lint test coverage mypy pyright

all: install lint test coverage mypy pyright

install: $(VENV_NAME)

# TODO: ensure protobuf is installed
$(PROTO_PY) $(PROTO_PYI): proto/config.proto
	protoc \
		-I="$(PROTO_DEF_DIR)" \
		--python_out="$(PROTO_OUT_DIR)" \
		--pyi_out="$(PROTO_OUT_DIR)" \
		"$(PROTO_DEF_DIR)"/config.proto

proto: $(PROTO_PY) $(PROTO_PYI)

$(VENV_NAME): pyproject.toml proto
	python3 -m venv $(VENV_NAME)
	$(PIP) install --upgrade pip
	$(PIP) install "setuptools>=62.0.0"
	$(PIP) install -e .

lint: $(VENV_NAME)
	$(PYTHON) -m black --verbose src tests scripts --exclude $(PROTO_OUT_DIR)

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
	git clean -ffdX
