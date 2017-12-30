#!/usr/bin/make
#
# Convenience makefile for helping deploy Lumina
# Copyright (C) 2010-2017 Svein Seldal <sveinse@seldal.com>
#

# Project root directory
# Get the path to the directory which this script sits in
this_file := $(abspath $(lastword $(MAKEFILE_LIST)))
base := $(abspath $(patsubst %/,%,$(dir $(this_file)))/../..)


# --- REMOTE SETTINGS
remotes := hus lum1 lum2 lum3

hus-HOST := svein@hus.local
hus-PATH := /home/svein/lumina-dev
hus-TYPE := xu

lum1-HOST := pi@lum1.local
lum1-PATH := /home/pi/lumina-dev
lum1-TYPE := rpi

lum2-HOST := pi@lum2.local
lum2-PATH := /home/pi/lumina-dev
lum2-TYPE := rpi

lum3-HOST := pi@lum3.local
lum3-PATH := /home/pi/lumina-dev
lum3-TYPE := rpi

pir-HOST := pi@pir.local
pir-PATH := /home/pi/lumina-dev
pir-TYPE := rpi
# -------------------

# Make a list of unique build targets
builders := $(sort $(foreach r,$(remotes),$($(r)-TYPE)))


#
# GENERIC RULES
# =============
help:
	@echo '   Targets:  $(shell grep '^[a-z]\S*:' Makefile | sed -e 's/:.*//g')'
	@echo "   Builders: $(builders)   ($(foreach b,$(buildtargets),*-$(b)))"
	@echo "   Remotes:  $(remotes)   ($(foreach r,$(remotetargets),*-$(r)))"

push-all:    $(foreach r,$(remotes),$(r)-push)
build-all:   $(foreach r,$(remotes),$(r)-build)
stop-all:    $(foreach r,$(remotes),$(r)-stop)
start-all:   $(foreach r,$(remotes),$(r)-start)
restart-all: $(foreach r,$(remotes),$(r)-restart)
status-all:  $(foreach r,$(remotes),$(r)-status)
install-all: $(foreach r,$(remotes),$(r)-install)
deploy-all:  $(foreach r,$(remotes),$(r)-deploy)

all: build-all install-all deploy-all


#
# REMOTE TARGETS
# ==============
define remotecmd
ssh -t $($(1)-HOST) -- /bin/sh -c '$(2)'
endef

# List of remote commands for make help
remotetargets=push run start stop logs build install deploy

define remotecmds
#--------------------------------------
# Common settings
$(eval $(1)-RUN:=-c contrib/deploy/test_$(1).json)
$(eval $(1)-DEBS:=dist-$($(1)-TYPE)/*.deb)
$(eval $(1)-DEPLOY:=contrib/deploy/deploy-$(1))

$(1)-push:
	rsync -av -FF --del $(base)/ $($(1)-HOST):$($(1)-PATH)

# Remote commands
$(1)-run: $(1)-push
	$(call remotecmd,$(1),"cd $($(1)-PATH) && exec python bin/lumina.py $($(1)-RUN)")
$(1)-start:
	$(call remotecmd,$(1),"sudo service lumina start")
$(1)-restart:
	$(call remotecmd,$(1),"sudo service lumina restart")
$(1)-status:
	$(call remotecmd,$(1),"sudo service lumina status")
$(1)-stop:
	$(call remotecmd,$(1),"sudo service lumina stop")
$(1)-logs:
	$(call remotecmd,$(1),"journalctl -f -u lumina")
$(1)-oldlogs:
	$(call remotecmd,$(1),"tail -f /var/log/messages")

# Crosslink remote target to the configured builder
$(1)-build: $($(1)-TYPE)-build

# Installation
$(1)-install: $(1)-push
	$(call remotecmd,$(1),"sudo dpkg -i $($(1)-PATH)/$($(1)-DEBS)")
$(1)-deploy: $(1)-push
	$(call remotecmd,$(1)," \
	    set -ex; \
		cd $($(1)-PATH); \
		if [ -x $($(1)-DEPLOY) ]; then \
			$($(1)-DEPLOY); \
		fi; \
	")

#--------------------------------------
endef

# Include the build rules into the makefile
$(foreach r,$(remotes),$(eval $(call remotecmds,$(r))))


#
# BUILD TARGETS
# =============

# List of remote commands for make help
buildtargets=build

define buildcmds
#--------------------------------------
$(1)-build:
	$(MAKE) -C $(base) docker-debs t=$(1)

#--------------------------------------
endef

# Include the build rules into the makefile
$(foreach b,$(builders),$(eval $(call buildcmds,$(b))))


#
# LOCAL TARGETS
# =============
local-run:
	cd ../../ && python bin/lumina.py -c contrib/deploy/test_local.json
local-run2:
	cd ../../ && python bin/lumina.py -c contrib/deploy/test_local2.json
local-run3:
	cd ../../ && python bin/lumina.py -c contrib/deploy/test_local3.json
