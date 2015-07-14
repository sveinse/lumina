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


# Rules for one client
define client
$(1)-sync:
	rsync -av --del -e ssh ./ pi@$(1):/home/pi/lumina-dev/ --exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc"
$(1)-run: $(1)-sync
	ssh -t pi@$(1) -- /bin/sh -c '"cd /home/pi/lumina-dev/ && exec ./lumina-$(1)"'
$(1)-test: $(1)-sync
	ssh -t pi@$(1) -- /bin/sh -c '"cd /home/pi/lumina-dev/ && exec ./lumina-test"'
$(1)-build: $(1)-sync
	ssh -t pi@$(1) -- /bin/sh -c '"cd /home/pi/lumina-dev/ && make build"'
$(1)-install: $(1)-sync $(1)-build
	ssh -t pi@$(1) -- /bin/sh -c '"cd /home/pi/lumina-dev/ && sudo dpkg -i lumina-$(1)_*.deb python-lumina_*.deb"'
$(1)-distclean: $(1)-sync
	ssh -t pi@$(1) -- /bin/sh -c '"cd /home/pi/lumina-dev/ && make distclean"'
$(1)-stop:
	ssh -t pi@$(1) -- /bin/sh -c '"sudo service lumina stop"'
$(1)-start:
	ssh -t pi@$(1) -- /bin/sh -c '"sudo service lumina start"'
$(1)-logs:
	ssh -t pi@$(1) -- /bin/sh -c '"tail -f /var/log/messages"'
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
	rm -rf lumina*.changes lumina*.deb python-lumina*.deb
