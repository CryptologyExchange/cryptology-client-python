.PHONY: all
all: clean sdist latex html

.PHONY: sdist
sdist:
	./venv/bin/python setup.py sdist

.PHONY: clean
clean:
	rm -rf html latex dist build .mypy_cache *.egg-info

.PHONY: latex
latex:
	./venv/bin/sphinx-build -b latex docs ./latex
	cd latex && make

.PHONY: html
html:
	./venv/bin/sphinx-build -b html docs ./html

.PHONY: publish
publish: clean html
	aws s3 sync --exact-timestamps --acl public-read html s3://client-python.docs.cryptology.com
