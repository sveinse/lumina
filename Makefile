#!/usr/bin/make


build:
	dpkg-buildpackage -b -uc -us -tc


distclean:
	dh_clean
	rm -rf build lumina.egg-info
	rm -rf ../lumina_*.changes
	rm -rf ../lumina_*.dsc
	rm -rf ../lumina_*.tar.gz
	rm -rf ../python-lumina_*.deb ../lumina_*.deb
