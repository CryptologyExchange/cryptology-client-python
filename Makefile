.PHONY: docs
docs:
	rm -rf _build
	./venv/bin/sphinx-build -b html docs ./_build
