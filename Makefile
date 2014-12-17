#!/usr/bin/make


help::
	@grep '^\S*:' Makefile

build::
	rm -f ../lumina_*.deb ../lumina_*.changes
	dpkg-buildpackage -b -uc -us

install::
	sudo dpkg -i ../lumina_*.deb


# Convenience for developing on 'lys'
lys-sync::
	rsync -av --del -e ssh ./ pi@lys:/home/pi/lumina/ --exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc"

lys-run: lys-sync
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina && exec ./luminad"'

lys-build: lys-sync
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina && make build"'

lys-install::
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina && make install"'


# Cleanups
clean::
	dh_clean
	rm -rf *.egg-info build

distclean:: clean
	rm -rf ../lumina_*.changes
	rm -rf ../lumina_*.dsc
	rm -rf ../lumina_*.tar.gz
	rm -rf ../lumina_*.deb
