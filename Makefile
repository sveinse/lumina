#!/usr/bin/make


build:
	rm -f ../lumina_*.deb
	dpkg-buildpackage -b -uc -us -tc

install:
	sudo dpkg -i ../lumina_*.deb


# Convenience for developing on 'lys'
sync-lys::
	rsync -av --del -e ssh ./ pi@lys:/home/pi/lumina/ --exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc"

run-lys: sync-lys
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina && exec ./luminad"'

build-lys: sync-lys
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina && make build"'

install-lys:
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina && make install"'

help:
	@grep '^\S*:' Makefile

# Cleanups
distclean:
	dh_clean
	rm -rf build lumina.egg-info
	rm -rf ../lumina_*.changes
	rm -rf ../lumina_*.dsc
	rm -rf ../lumina_*.tar.gz
	rm -rf ../lumina_*.deb
