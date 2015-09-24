"""setup.py - Setup file for volbot"""

import os
from setuptools import setup, find_packages

setup(
    name='volbot',
    version='0.1.0',
    description='IRC bot for the University of Tennessee channel.',
    packages=find_packages(),
    package_data={
        'volbot.volbot.extra': ['*'],
    },
    include_package_data=True,
    install_requires=[
        'irc',
        'markovify',
        'pymongo',
        'requests',
        'wikipedia',
        'praw',
        'microsofttranslator',
    ],
    entry_points={
        'console_scripts': ['volbot=volbot.volbot:main', 'volbot-curses=volbot.scripts.curses:main',
                            'volbot-dirtytalk=volbot.scripts.dirtytalk:main'],
    }
)
