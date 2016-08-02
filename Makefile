#!/usr/bin/make
#
# Convenience makefile for helping build and development of Lumina
# Copyright (C) 2010-2016 Svein Seldal <sveinse@seldal.com>
#

install-debs=lumina_*.deb python-lumina_*.deb
debfiles=$(install-debs) lumina_*.changes


help:
	@grep '^\S*:' Makefile

build::
	rm -f $(foreach f,$(debfiles),../$(f))
	dpkg-buildpackage -b -uc -us
	mkdir -p debs
	rm -f $(foreach f,$(debfiles),debs/$(f))
	mv $(foreach f,$(debfiles),../$(f)) debs

install:
	sudo dpkg -i $(foreach f,$(install-debs),debs/$(f))

version:
	@head -n 1 debian/changelog | sed -e "s/^.*(\(.*\)).*/\\1/"

newversion: version
	@test $${V:?"usage: make $@ V=<version>"}
	sed -i -e "s/^\(\\w\+\) \+(.*)/\\1 ($(V))/" \
	       -e "s/\(--.*>\).*$$/\\1  $$(date -R)/" debian/changelog
	sed -i -e "s/version='.*'/version='$(V)'/" setup.py
	grep -e 'version=' setup.py
	cat debian/changelog


#
# REMOTE DEPLOYMENT
# =================
remotes = hus lys hw50

hus-HOST=svein@hus.local
hus-HOME=/home/svein/lumina-dev
hus-deploy-from=debs-hus

lys-HOST=pi@lys.local
lys-HOME=/home/pi/lumina-dev
lys-deploy-from=debs-lys

hw50-HOST=pi@hw50.local
hw50-HOME=/home/pi/lumina-dev
hw50-deploy-from=debs-lys


start:: $(foreach r,$(remotes),$(r)-start)
stop:: $(foreach r,$(remotes),$(r)-stop)
sync:: $(foreach r,$(remotes),$(r)-sync)

deploy::
	$(MAKE) clean
	$(MAKE) hus-build hus-install
	$(MAKE) lys-build lys-install
	$(MAKE) hw50-install


define remcmd
ssh -t $($(1)-HOST) -- /bin/sh -c '$(2)'
endef

define remote
$(1)-sync:
	rsync -av --del -e ssh ./ $($(1)-HOST):$($(1)-HOME) -FF
#$(1)-run: $(1)-sync
#	$(call remcmd,$(1),"cd $($(1)-HOME) && exec ./lumid $($(1)-OPTS)")
#$(1)-test: $(1)-sync
#	$(call remcmd,$(1),"cd $($(1)-HOME) && exec ./lumina-test")
$(1)-build:
	rm -rf $(1)-debs/*
	$(MAKE) $(1)-sync
	$(call remcmd,$(1),"cd $($(1)-HOME) && make build")
	rsync -av --del -e ssh $($(1)-HOST):$($(1)-HOME)/debs/* debs-$(1)/
$(1)-deploy:
	rsync -av --del -e ssh $($(1)-deploy-from)/ $($(1)-HOST):$($(1)-HOME)/debs/
$(1)-install: $(1)-sync $(1)-deploy
	$(call remcmd,$(1)," \
		set -ex; \
		cd $($(1)-HOME); \
		make install; \
		if [ -x 'deploy/deploy-$(1)' ]; then \
		    deploy/deploy-$(1); \
		fi \
	")
$(1)-clean:
	$(call remcmd,$(1),"cd $($(1)-HOME) && make clean")
$(1)-distclean:
	$(call remcmd,$(1),"cd $($(1)-HOME) && make distclean")
$(1)-wipe:
	$(call remcmd,$(1),"cd $($(1)-HOME) && rm -rf *")
$(1)-stop:
	$(call remcmd,$(1),"sudo service lumina stop")
$(1)-start:
	$(call remcmd,$(1),"sudo service lumina start")
$(1)-logs:
	$(call remcmd,$(1),"tail -f /var/log/messages")
endef


# Include the remotes into this makefile
$(eval $(call remote,hus))
$(eval $(call remote,lys))
$(eval $(call remote,hw50))



# Cleanups
clean::
	dh_clean
	-(cd contrib/telldus/telldus-core-2.1.2 && dh_clean)
	rm -rf *.egg-info build
	rm -f $(foreach f,$(debfiles),../$(f) $(f) debs/$(f) debs-*/$(f))
	-find debs/ debs-*/ -type d -empty -delete

distclean:: clean
	rm -rf debs/ debs-*/
