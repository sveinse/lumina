#!/usr/bin/make


help:
	@grep '^\S*:' Makefile

build::
	rm -f ../lumina*.deb ../python-lumina*.deb ../lumina_*.changes
	dpkg-buildpackage -b -uc -us
	mv ../lumina*.deb ../python-lumina*.deb ../lumina_*.changes .

install:
	sudo dpkg -i ../lumina_*.deb

version:
	head -n 1 debian/changelog

newversion: version
	@echo "lumina ($(V)) unstable; urgency=low" >debian/changelog
	@echo "" >>debian/changelog
	@echo "  * See git history" >>debian/changelog
	@echo "" >>debian/changelog
	@echo " -- Svein Seldal <sveinse@seldal.com>  $$(date -R)" >>debian/changelog
	cat debian/changelog

# Specific options
lys-OPTS=--config=conf/lys-debug.conf
hw50-OPTS=--config=conf/hw50.conf

lys-HOST=pi@lys
hw50-HOST=pi@10.5.5.15

rhome=/home/pi/lumina-dev/

define remote
ssh -t $($(1)-HOST) -- /bin/sh -c '$(2)'
endef

# Rules for one client
define client
$(1)-sync:
	rsync -av --del -e ssh ./ $($(1)-HOST):$(rhome) --exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc"
$(1)-run: $(1)-sync
	$(call remote,$(1),"cd $(rhome) && exec ./lumid $($(1)-OPTS)")
$(1)-test: $(1)-sync
	$(call remote,$(1),"cd $(rhome) && exec ./lumina-test")
$(1)-build: $(1)-sync
	$(call remote,$(1),"cd $(rhome) && make build")
	rsync -av --del -e ssh $($(1)-HOST):$(rhome)/*.deb $($(1)-HOST):$(rhome)/*.changes pi-debs/
$(1)-install: $(1)-sync
	$(call remote,$(1),"cd $(rhome) && sudo dpkg -i pi-debs/lumina-$(1)_*.deb pi-debs/python-lumina_*.deb")
$(1)-distclean: $(1)-sync
	$(call remote,$(1),"cd $(rhome) && make distclean")
$(1)-stop:
	$(call remote,$(1),"sudo service lumina stop")
$(1)-start:
	$(call remote,$(1),"sudo service lumina start")
$(1)-logs:
	$(call remote,$(1),"tail -f /var/log/messages")
endef


# Make
$(eval $(call client,lys))
$(eval $(call client,hw50))



# Cleanups
clean::
	dh_clean
	rm -rf *.egg-info build

distclean:: clean
	rm -rf ../lumina_*.changes ../lumina_*.dsc ../lumina_*.tar.gz ../lumina*.deb ../python-lumina*.deb
	rm -rf lumina*.changes lumina*.deb python-lumina*.deb pi-debs
