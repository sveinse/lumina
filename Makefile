#!/usr/bin/make


help::
	@grep '^\S*:' Makefile

build::
	rm -f ../lumina*.deb ../python-lumina*.deb ../lumina_*.changes
	dpkg-buildpackage -b -uc -us
	mv ../lumina*.deb ../python-lumina*.deb ../lumina_*.changes .

install::
	sudo dpkg -i ../lumina_*.deb

newversion::
	head -n 1 debian/changelog
	@echo "lumina ($(V)) unstable; urgency=low" >debian/changelog
	@echo "" >>debian/changelog
	@echo "  * See git history" >>debian/changelog
	@echo "" >>debian/changelog
	@echo " -- Svein Seldal <sveinse@seldal.com>  $$(date -R)" >>debian/changelog
	cat debian/changelog



# Convenience for developing on 'lys'
lys-sync::
	rsync -av --del -e ssh ./ pi@lys:/home/pi/lumina-dev/ --exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc"

lys-run: lys-sync
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina-dev/ && exec ./lumina-lys"'

lys-build: lys-sync
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina-dev/ && make build"'

#lys-install::
#	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina-dev/ && make install"'

lys-install:
	ssh -t pi@lys -- /bin/sh -c '"cd /home/pi/lumina-dev/ && sudo dpkg -i lumina-lys_*.deb python-lumina_*.deb"'


# Convenience for developing on 'hw50'
hw50-sync::
	rsync -av --del -e ssh ./ pi@hw50:/home/pi/lumina-dev/ --exclude="/debian/lumina" --exclude="/build" --exclude="/lumina.egg-info" --exclude="*.pyc"

hw50-run: hw50-sync
	ssh -t pi@hw50 -- /bin/sh -c '"cd /home/pi/lumina-dev/ && exec ./lumina-hw50"'

hw50-build: hw50-sync
	ssh -t pi@hw50 -- /bin/sh -c '"cd /home/pi/lumina-dev/ && make build"'

#hw50-install::
#	ssh -t pi@hw50 -- /bin/sh -c '"cd /home/pi/lumina-dev/ && make install"'

hw50-install:
	ssh -t pi@hw50 -- /bin/sh -c '"cd /home/pi/lumina-dev/ && sudo dpkg -i lumina-hw50_*.deb python-lumina_*.deb"'


# Cleanups
clean::
	dh_clean
	rm -rf *.egg-info build

distclean:: clean
	rm -rf ../lumina_*.changes ../lumina_*.dsc ../lumina_*.tar.gz ../lumina*.deb ../python-lumina*.deb
	rm -rf lumina*.changes lumina*.deb python-lumina*.deb
