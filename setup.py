import sys

from setuptools import setup

if sys.version_info < (3, 6):
    raise ImportError('cryptology-client-python only supports python3.6 and newer')

setup(
    name='cryptology-client-python',
    version='0.6.2',
    description='cryptology webscoket client',
    author='Cryptology',
    author_email='victor@cryptology.com',
    packages=['cryptology'],
    python_requires='>= 3.6',
    install_requires=[
        'aiodns',
        'aiohttp >= 2.3.6',
        'cchardet',
        'cryptography >= 2.1.4',
        'pytz >= 2013.6'
    ]
)
