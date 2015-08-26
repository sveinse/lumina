from setuptools import setup, find_packages

setup(
    name='lumina',
    version='0.1',
    description="Home Theater Controller",
    author='Svein Seldal',
    author_email='sveinse@seldal.com',
    license='GPL2',

    packages = [ 'lumina' ],

    scripts = [ 'lumina-lys','lumina-hw50','lumid' ],

    data_files = [ ('share/lumina/www',     ['www/index.html' ] ),
                   ('share/lumina/www/css', ['www/css/lumina.css' ] ),
                   ('share/lumina/www/js',  ['www/js/lumina.js' ] ),
               ]
)
