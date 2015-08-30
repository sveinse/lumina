from setuptools import setup, find_packages

setup(
    name='lumina',
    version='0.1',
    description="Home Theater Controller",
    author='Svein Seldal',
    author_email='sveinse@seldal.com',
    license='MIT',

    packages = [ 'lumina', 'lumina/plugins' ],

    scripts = [ 'lumid' ],

    data_files = [ ('share/lumina/conf',    [ 'conf/lys.conf',
                                              'conf/hw50.conf' ] ),
                   ('share/lumina/www',     [ 'www/app.js',
                                              'www/index.html',
                                              'www/luminacomm.js',
                                              'www/lumina.css',
                                              'www/old.html',
                                              'www/old.js' ] ),
               ]
)
