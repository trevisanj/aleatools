import sys
# if sys.version_info[0] < 3:
#     print("Python version detected:\n*****\n{0!s}\n*****\nCannot run, must be using Python 3".format(sys.version))
#     sys.exit()

from setuptools import setup, find_packages
from glob import glob

setup(
    name = 'aleatools',
    packages = find_packages(),
    include_package_data=True,
    version = '1999-B.C.',
    license = 'GNU GPLv3',
    platforms = 'any',
    description = 'Aleatory Tools',
    author = 'Julio Trevisan',
    author_email = 'juliotrevisan@gmail.com',
    url = 'http://github.com/trevisanj/aleatools',
    keywords= [],
    install_requires = ['a99>=17.12.26', 'pycrypto'],
    python_requires = '>=3',
    scripts = glob('aleatools/scripts/*.py')
)
