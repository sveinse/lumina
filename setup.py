from setuptools import setup, find_packages

setup(
    name='lumina',
    version='0.1',
    description="Home Cinema controller",
    author='Svein Seldal',
    author_email='sveinse@seldal.com',
    license='GPL2',

    #scripts = [ 'lumina.py' ],
    #package_dir = {'': 'src'},

    packages = [ 'lumina' ],
    entry_points={
        'console_scripts': [
            'lumina = lumina.lumina:main',
        ]
    }
)
