.PHONY: all
all: clean latex html

.PHONY: clean
clean:
	rm -rf html latex

.PHONY: latex
latex:
	./venv/bin/sphinx-build -b latex docs ./latex
	cd latex && make

.PHONY: html
html:
	./venv/bin/sphinx-build -b html docs ./html
