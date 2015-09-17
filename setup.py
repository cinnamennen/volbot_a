"""setup.py - Setup file for volbot"""


from setuptools import setup, find_packages


setup(
    name = 'volbot',
    version = '0.1.0',
    description = 'IRC bot for the University of Tennessee channel.',
    packages = find_packages(),
    package_data = {
        'volbot.volbot.extra': ['*'],
    },
    include_package_data = True,
    entry_points = {
        'console_scripts': ['volbot=volbot.volbot:main', 'volbot-curses=volbot.scripts.curses:main'],
    }
)
