from setuptools import setup, find_packages

setup(
    name='lumina',
    version='0.1',
    description="Home Theater Controller",
    author='Svein Seldal',
    author_email='sveinse@seldal.com',
    license='GPL2',

    scripts = [ 'luminad' ],
    packages = [ 'lumina' ],

    #entry_points={
    #    'console_scripts': [
    #        'luminad = lumina.lumina:main',
    #    ]
    #}
)
