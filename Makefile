#!/usr/bin/make
#
# Convenience makefile for helping build and packaging of Lumina
# Copyright (C) 2010-2017 Svein Seldal <sveinse@seldal.com>
#

# Default builddir directory and output directory
build?=build
output?=dist

debfiles=lumina_*.deb python-lumina_*.deb lumina_*.changes
versionfile=lumina/__init__.py

define builddeb
mkdir -p $(1)
rsync -av -FF --del --filter='- /dist/' --filter='- /dist*/' ./ $(1)/
make -C $(1)/ debian/changelog
cd $(1) && $(3) dpkg-buildpackage -b -uc -us
mkdir -p $(2) && mv $(foreach f,$(debfiles),$(f)) $(2)/
endef



help:
	@echo "This Makefile supports building and packaging Lumina"
	@echo '   Targets:  $(shell grep '^[a-z]\S*:' Makefile | sed -e 's/:.*//g')'

debs::
	$(call builddeb,$(build),$(output))

docker-debs:
	@test $${t:?"usage: make $@ t=<target>"}
	$(call builddeb,$(build)-$(t),$(output)-$(t),$(PWD)/contrib/broot/run-docker $(t) --)

version:
	@python bin/lumina-build.py version $(versionfile)

newversion:
	@test $${v:?"usage: make $@ v=<version>"}
	@python bin/lumina-build.py newversion $(versionfile) $(v)

mk-venv:
	virtualenv venv
	. venv/bin/activate; \
	   pip install -e .; \
	   lumina --help; \
	   deactivate

debian/changelog: debian/changelog.in
	set -e; \
		cmd_version='python bin/lumina-build.py version $(versionfile)' \
		cmd_date='git log -n1 --format="%aD"' \
		cmd_author='git log -n1 --format="%an"' \
		cmd_email='git log -n1 --format="%ae"' \
		cmd_subject='git log -n1 --format="%B"' \
		python bin/lumina-build.py parse $< >$@

sdist:
	python setup.py sdist

bdist:
	python setup.py bdist

clean::
	rm -rf *.egg-info $(build) debian/changelog dist

distclean:: clean
	rm -rf venv $(build) $(build)-* $(output) $(output)-* *.deb *.changes
