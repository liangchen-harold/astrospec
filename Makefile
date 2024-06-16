.PHONY: build deploy

all: build

build:
	python -m build

deploy: build
	python -m twine upload dist/*
