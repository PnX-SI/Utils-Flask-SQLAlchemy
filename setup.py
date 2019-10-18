# coding: utf-8

# Do not import unicode_literals it generate an error when install module with pip
from __future__ import (print_function,
                        absolute_import, division)

import re
import setuptools


def get_version(path="./VERSION"):
    """ Return the version of by with regex intead of importing it"""
    version_number = open(path, "rt").read()
    return version_number


setuptools.setup(
    name='utils-flask-sqlalchemy',
    version=get_version(),
    description="Python lib of tools for Flask and SQLAlchemy",
    long_description=open('README.md', encoding="utf-8").read().strip(),
    author="Les parcs nationaux de France",
    url='https://github.com/PnX-SI/Utils-Flask-SQLAlchemy',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    install_requires=list(open('requirements.txt', 'r')),
    include_package_data=True,
    zip_safe=False,
    keywords='ww',
    classifiers=['Development Status :: 1 - Planning',
                 'Intended Audience :: Developers',
                 'Natural Language :: English',
                 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'License :: OSI Approved :: GNU Affero General Public License v3',
                 'Operating System :: OS Independent'],
)
