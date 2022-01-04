import setuptools
from pathlib import Path


root_dir = Path(__file__).absolute().parent
with (root_dir / 'VERSION').open() as f:
    version = f.read()
with (root_dir / 'README.md').open() as f:
    long_description = f.read()
with (root_dir / 'requirements.in').open() as f:
    requirements = f.read().splitlines()


setuptools.setup(
    name='utils-flask-sqlalchemy',
    version=version,
    description="Python lib of tools for Flask and SQLAlchemy",
    long_description=long_description,
    long_description_content_type='text/markdown',
    maintainer='Parcs nationaux des Écrins et des Cévennes',
    maintainer_email='geonature@ecrins-parcnational.fr',
    url='https://github.com/PnX-SI/Utils-Flask-SQLAlchemy',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    install_requires=requirements,
    extras_require={
        'tests': [
            'pytest',
            'geoalchemy2',
            'shapely',
            'jsonschema',
            'flask-marshmallow',
            'marshmallow-sqlalchemy',
        ],
    },
    entry_points={
        'alembic': [
            'migrations = utils_flask_sqla.migrations:versions',
        ],
        'pytest11': [
            'sqla = utils_flask_sqla.tests.plugin',
        ],
    },
    classifiers=['Development Status :: 1 - Planning',
                 'Intended Audience :: Developers',
                 'Natural Language :: English',
                 'Programming Language :: Python :: 3',
                 'License :: OSI Approved :: GNU Affero General Public License v3',
                 'Operating System :: OS Independent'],
)
