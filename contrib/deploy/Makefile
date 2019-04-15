#!/usr/bin/make
#
# Convenience makefile for helping deploy Lumina
# Copyright (C) 2010-2018 Svein Seldal <sveinse@seldal.com>
#

# Project root directory
# Get the path to the directory which this script sits in
this_file := $(abspath $(lastword $(MAKEFILE_LIST)))
base := $(abspath $(patsubst %/,%,$(dir $(this_file)))/../..)
versionfile=$(base)/lumina/__init__.py
version := $(shell python $(base)/bin/lumina-build.py version $(versionfile))

# --- REMOTE SETTINGS
remotes_debian := hus lum1 lum2 lum3
remotes_docker := lys

lys-HOST := svein@kul.sol
lys-PATH := /home/svein/lumina-dev
lys-TYPE := docker

hus-HOST := svein@hus.sol
hus-PATH := /home/svein/lumina-dev
hus-TYPE := xu

lum1-HOST := pi@lum1.sol
lum1-PATH := /home/pi/lumina-dev
lum1-TYPE := rpi

lum2-HOST := pi@lum2.sol
lum2-PATH := /home/pi/lumina-dev
lum2-TYPE := rpi

lum3-HOST := pi@lum3.sol
lum3-PATH := /home/pi/lumina-dev
lum3-TYPE := rpi

pir-HOST := pi@pir.sol
pir-PATH := /home/pi/lumina-dev
pir-TYPE := rpi
# -------------------

# Make a list of unique build targets
remotes := $(remotes_debian) $(remotes_docker)
builders := $(sort $(foreach r,$(remotes),$($(r)-TYPE)))


#
# GENERIC RULES
# =============
help:
	@echo '   Targets:  $(shell grep '^[a-z]\S*:' Makefile | sed -e 's/:.*//g')'
	@echo "   Builders: $(builders)   ($(foreach b,$(buildtarget_names),*-$(b)))"
	@echo "   Remotes:  $(remotes)   ($(foreach r,$(remotetarget_names),*-$(r)))"

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
remotetarget_names=push run start stop logs build install deploy

define remotecmds_debian
#--------------------------------------
# Remote Debian targets
$(eval $(1)-RUN:=server -c contrib/deploy/test_$(1).json)
$(eval $(1)-DEBS:=dist-$($(1)-TYPE)/*.deb)
$(eval $(1)-DEPLOY:=contrib/deploy/deploy-$(1))

$(1)-push:
	rsync -av -FF --delete-after $(base)/ $($(1)-HOST):$($(1)-PATH)

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
$(foreach r,$(remotes_debian),$(eval $(call remotecmds_debian,$(r))))


define remotecmds_docker
#--------------------------------------
# Remote Docker targets

$(1)-push:
	rsync -av -FF --delete-after $(base)/ $($(1)-HOST):$($(1)-PATH)

# Remote commands
$(1)-start:
	$(call remotecmd,$(1),"sudo docker start lumina")
$(1)-restart:
	$(call remotecmd,$(1),"sudo docker restart lumina")
#$(1)-status:
#	$(call remotecmd,$(1),"sudo service lumina status")
$(1)-stop:
	$(call remotecmd,$(1),"sudo docker stop lumina")
#$(1)-logs:
#	$(call remotecmd,$(1),"journalctl -f -u lumina")
#$(1)-oldlogs:
#	$(call remotecmd,$(1),"tail -f /var/log/messages")
$(1)-build:

# Installation
$(1)-install: $(1)-push
	$(call remotecmd,$(1),"cd $($(1)-PATH) && sudo lumina_version=$(version) make docker-image")
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
$(foreach r,$(remotes_docker),$(eval $(call remotecmds_docker,$(r))))


#
# BUILD TARGETS
# =============
rpi-build:
	$(MAKE) -C $(base) docker-debs t=rpi
xu-build:
	$(MAKE) -C $(base) docker-debs t=xu
docker-build:
	$(MAKE) -C $(base) docker-image

# List of remote commands for make help
buildtarget_names=build


#
# LOCAL TARGETS
# =============
local-run:
	cd ../../ && venv/bin/lumina server -c contrib/deploy/test_local.json
local-run2:
	cd ../../ && venv/bin/lumina.py server -c contrib/deploy/test_local2.json
local-run3:
	cd ../../ && venv/bin/lumina.py server -c contrib/deploy/test_local3.json
docker-run: docker-build
	mkdir -p tmp.lumina && cp test_docker.json tmp.lumina/lumina.json
	docker run -it --rm \
		-v $(PWD)/tmp.lumina:/etc/lumina:ro \
		-p8888:8888 -p5326:5326 \
		lumina
	rm -rf tmp.lumina
