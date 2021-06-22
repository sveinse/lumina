#!/usr/bin/make
#
# Convenience makefile for helping build and packaging of Lumina
# Copyright (C) 2010-2018 Svein Seldal <sveinse@seldal.com>
#

# Default builddir directory and output directory
build?=build
output?=dist

python=$(if $(shell which python),python,python3)

debfiles=lumina_*.deb lumina_*.changes lumina_*.buildinfo python-lumina_*.deb python3-lumina_*.deb
versionfile=lumina/__init__.py

# Get the path to the directory which this script sits in
this_file := $(abspath $(lastword $(MAKEFILE_LIST)))
base := $(patsubst %/,%,$(dir $(this_file)))

# Use shell functions rather than the python script, as this is executed on target
ifeq ($(version),)
version := $(shell cat $(base)/lumina/__init__.py | sed -n "s/__version__\s*=\s*'\(.*\)'/\1/p")
endif

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
	$(call builddeb,$(build)-$(t),$(output)-$(t),$(base)/contrib/docker/run-docker $(t) --)

docker-image:
	docker build -t lumina:$(version) .

httpd:
	cd www && ../venv/bin/twistd -n web --listen=tcp:8888 --path .

version:
	@echo $(version)

newversion:
	@test $${v:?"usage: make $@ v=<version>"}
	@$(python) bin/lumina-build.py newversion $(versionfile) $(v)

mk-venv:
	virtualenv venv
	venv/bin/pip install -e .
	venv/bin/lumina --help

debian/changelog: debian/changelog.in
	set -e; \
		cmd_version='$(python) bin/lumina-build.py version $(versionfile)' \
		cmd_date='git log -n1 --format="%aD"' \
		cmd_author='git log -n1 --format="%an"' \
		cmd_email='git log -n1 --format="%ae"' \
		cmd_subject='git log -n1 --format="%B"' \
		$(python) bin/lumina-build.py parse $< >$@

sdist:
	$(python) setup.py sdist

bdist:
	$(python) setup.py bdist

clean::
	rm -rf *.egg-info *.buildinfo $(build) debian/changelog dist

distclean:: clean
	rm -rf venv $(build) $(build)-* $(output) $(output)-* *.deb *.changes
