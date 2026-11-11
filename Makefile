PYTHON ?= python3

.PHONY: characterize test verify
characterize:
	$(PYTHON) scripts/characterize.py
test:
	$(PYTHON) -m pytest -q
verify: characterize test
