#!/usr/bin/make
#
# Convenience makefile for helping build and development of Lumina
# Copyright (C) 2010-2016 Svein Seldal <sveinse@seldal.com>
#

install-debs=lumina_*.deb python-lumina_*.deb
debfiles=$(install-debs) lumina_*.changes

docker=$(PWD)/contrib/broot/run-docker

# --- BUILD settings
builders=local xenial xu rpi

local-BUILD=build
local-CMD=
local-DEBS=debs

xenial-BUILD=build-xenial
xenial-CMD=$(docker) xenial --
xenial-DEBS=debs-xenial

xu-BUILD=build-xu
xu-CMD=$(docker) xu --
xu-DEBS=debs-xu

rpi-BUILD=build-rpi
rpi-CMD=$(docker) rpi --
rpi-DEBS=debs-rpi

# --- REMOTE settings
remotes = hus lum1 lum2

hus-HOST=svein@hus.local
hus-PATH=/home/svein/lumina-dev
hus-DEBS=$(xu-DEBS)

lum1-HOST=pi@lum1.local
lum1-PATH=/home/pi/lumina-dev
lum1-DEBS=$(rpi-DEBS)

lum2-HOST=pi@lum2.local
lum2-PATH=/home/pi/lumina-dev
lum2-DEBS=$(rpi-DEBS)


#
# GENERIC RULES
# =============
help:
	@echo '   Targets:  $(shell grep '^[a-z]\S*:' Makefile | sed -e 's/:.*//g')'
	@echo "   Builders: $(builders)   ($(foreach b,$(buildtargets),*-$(b)))"
	@echo "   Remotes:  $(remotes)   ($(foreach r,$(remotetargets),*-$(r)))"

build:
	rm -f $(foreach f,$(debfiles),../$(f))
	dpkg-buildpackage -b -uc -us
	mkdir -p debs
	rm -f $(foreach f,$(debfiles),debs/$(f))
	mv $(foreach f,$(debfiles),../$(f)) debs

version:
	@head -n 1 debian/changelog | sed -e "s/^.*(\(.*\)).*/\\1/"

newversion: version
	@test $${V:?"usage: make $@ V=<version>"}
	sed -i -e "s/^\(\\w\+\) \+(.*)/\\1 ($(V))/" \
	       -e "s/\(--.*>\).*$$/\\1  $$(date -R)/" debian/changelog
	sed -i -e "s/version='.*'/version='$(V)'/" setup.py
	grep -e 'version=' setup.py
	cat debian/changelog

mk-venv:
	virtualenv venv
	. venv/bin/activate; \
	   pip install twisted; \
	   pip install -e .; \
	   lumina --help; \
	   deactivate


#
# BUILD TARGETS
# =============
buildtargets=push pull build
define buildcmds
#---------------
$(1)-push:
	rsync -av -FF --del --filter='- /debs/' --filter='- /debs*/' ./ $($(1)-BUILD)

$(1)-pull:
	rsync -av --del $($(1)-BUILD)/debs/ $($(1)-DEBS)

$(1)-build: $(1)-push
	$($(1)-CMD) $(MAKE) -C $($(1)-BUILD) build

$($(1)-DEBS): $(1)-build $(1)-pull

endef

# Include the build rules into the makefile
$(foreach b,$(builders),$(eval $(call buildcmds,$(b))))


#
# REMOTE TARGETS
# ==============
define remotecmd
ssh -t $($(1)-HOST) -- /bin/sh -c '$(2)'
endef

remotetargets=push run start stop logs build install deploy
define remotecmds
#---------------
# Commands for development use
$(1)-push:
	rsync -av -FF --del ./ $($(1)-HOST):$($(1)-PATH)

# Remote commands
$(1)-run: $(1)-push
	$(call remotecmd,$(1),"cd $($(1)-PATH) && exec python lumina.py $(O)")
$(1)-start:
	$(call remotecmd,$(1),"sudo service lumina start")
$(1)-stop:
	$(call remotecmd,$(1),"sudo service lumina stop")
$(1)-logs:
	$(call remotecmd,$(1),"journalctl -f -u lumina")

# Crosslink remote target to the configured builder
$(1)-build: $($(1)-DEBS)

# Installation
$(1)-install: $(1)-build $(1)-push
	$(call remotecmd,$(1),"sudo dpkg -i $($(1)-PATH)/$($(1)-DEBS)/*.deb")
$(1)-deploy: $(1)-install
	$(call remotecmd,$(1)," \
	    set -ex; \
		cd $($(1)-PATH); \
		if [ -x deploy/deploy-$(1) ]; then \
		  deploy/deploy-$(1); \
		fi; \
	")

endef

# Include the build rules into the makefile
$(foreach r,$(remotes),$(eval $(call remotecmds,$(r))))


# --- All-rules
build-all:   $(foreach r,$(remotes),$($(r)-DEBS))
push-all:    $(foreach r,$(remotes),$(r)-push)
stop-all:    $(foreach r,$(remotes),$(r)-stop)
start-all:   $(foreach r,$(remotes),$(r)-start)
install-all: $(foreach r,$(remotes),$(r)-install)
deploy-all:  $(foreach r,$(remotes),$(r)-deploy)


# --- Cleanups
clean::
	#-dh_clean
	rm -rf *.egg-info build
	rm -rf $(foreach b,$(builders),$($(b)-BUILD))

distclean:: clean
	rm -rf $(foreach b,$(builders),$($(b)-DEBS))
