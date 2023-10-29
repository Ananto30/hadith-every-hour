.PHONY: help install-lint
install-lint:
	@echo "Installing lint dependencies..."
	@pip install isort black flake8 mypy

.PHONY: lint
lint:
	@echo "Running lint..."
	@isort --check-only --diff .
	@black --check --diff .
	@flake8 .

.PHONY: format
format:
	@echo "Running format..."
	@isort .
	@black . -l 79

.PHONY: mypy
mypy:
	@echo "Running mypy..."
	@mypy .

.PHONY: help mypy-install-types
mypy-install-types:
	@echo "Running mypy-stubgen..."
	@mypy --install-types --non-interactive .

.PHONY: tweet
tweet:
	@echo "Tweeting..."
	@python main.py tweet

.PHONY: fb
fb:
	@echo "Posting to Facebook..."
	@python main.py fb