from setuptools import setup, find_packages
from glob import glob

setup(
    name = 'aleatools',
    packages = find_packages(),
    include_package_data=True,
    version = '20.02.23.0',
    license = 'GNU GPLv3',
    platforms = 'any',
    description = 'Aleatory Tools',
    author = 'Julio Trevisan',
    author_email = 'juliotrevisan@gmail.com',
    url = 'http://github.com/trevisanj/aleatools',
    keywords= [],
    install_requires = ['a107>=20.02.23.0', 'pycrypto'],
    python_requires = '>=3',
    scripts = glob('aleatools/scripts/*.py')
)
