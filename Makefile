#!/usr/bin/make
#
# Convenience makefile for helping build and development of Lumina
# Copyright (C) 2010-2016 Svein Seldal <sveinse@seldal.com>
#

debfiles=lumina_*.deb python-lumina_*.deb lumina_*.changes

help:
	@grep '^\S*:' Makefile

build::
	rm -f $(foreach f,$(debfiles),../$(f))
	dpkg-buildpackage -b -uc -us
	mkdir -p debs
	rm -f $(foreach f,$(debfiles),debs/$(f))
	mv $(foreach f,$(debfiles),../$(f)) debs

install:
	sudo dpkg -i *.deb

version:
	@head -n 1 debian/changelog | sed -e "s/^.*(\(.*\)).*/\\1/"

newversion: version
	@test $${V:?"usage: make $@ V=<version>"}
	sed -i -e "s/^\(\\w\+\) \+(.*)/\\1 ($(V))/" \
	       -e "s/\(--.*>\).*$$/\\1  $$(date -R)/" debian/changelog
	sed -i -e "s/version='.*'/version='$(V)'/" setup.py
	grep -e 'version=' setup.py
	cat debian/changelog

deploy:
	$(MAKE) distclean
	$(MAKE) hus-build hus-install
	$(MAKE) lys-deploy lys-install
	$(MAKE) hw50-deploy hw50-install


# Specific options
#hus-OPTS=--config=conf/hus.conf
#lys-OPTS=--config=conf/lys-debug.conf
#hw50-OPTS=--config=conf/hw50.conf

#lys-HOST=pi@lys.local
#hw50-HOST=pi@hw50.local

#lys-HOME=/home/pi/lumina-dev/
#hw50-HOME=/home/pi/lumina-dev/

#
# REMOTE DEPLOYMENT
# =================
hus-HOST=svein@hus.local
hus-HOME=/home/svein/lumina-dev

lys-HOST=pi@lys.local
lys-HOME=/home/pi/lumina-dev

hw50-HOST=pi@lys.local
hw50-HOME=/home/pi/lumina-dev

deploy-from-debs=debs-hus


rsync-exclude=--exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc" --exclude="/.git*" --exclude="*~" --exclude="from_*" --exclude="/debian/tmp" --exclude="/debian/python-lumina" --exclude="/debian/lumina" --exclude="/debs-*/" --exclude="/debs/" --exclude="/debian/*debhelper*" --exclude="/debian/*.substvars" --exclude="/debian/files"

define remcmd
ssh -t $($(1)-HOST) -- /bin/sh -c '$(2)'
endef

define remote
$(1)-sync:
	rsync -av --del -e ssh ./ $($(1)-HOST):$($(1)-HOME) $(rsync-exclude)
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
	rsync -av --del -e ssh $(deploy-from-debs)/ $($(1)-HOST):$($(1)-HOME)/debs/
$(1)-install:
	$(call remcmd,$(1),"cd $($(1)-HOME)/debs && echo sudo dpkg -i *.deb")
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
	rm -rf *.egg-info build

distclean:: clean
	rm -rf ../lumina_*.changes ../lumina_*.dsc ../lumina_*.tar.gz ../lumina*.deb ../python-lumina*.deb
	rm -rf lumina*.changes lumina*.deb python-lumina*.deb debs/ debs-*/
