# Makefile
.PHONY: help

help:
	@echo "Commands:"
	@echo "  run       - run the application"
	@echo "  test      - run the tests"
	@echo "  lint      - lint the code"
	@echo "  fmt       - format the code"

run:
	./scripts/local_boot.sh

test:
	./scripts/run_tests.sh

lint:
	./scripts/lint.sh

fmt:
	black .
	ruff --fix .
	prettier --write .
