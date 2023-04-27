import os
import re

from setuptools import find_packages, setup


def read(*names):
    values = dict()
    for name in names:
        filename = name + ".rst"
        if os.path.isfile(filename):
            fd = open(filename)
            value = fd.read()
            fd.close()
        else:
            value = ""
        values[name] = value
    return values


long_description = """
%(README)s

News
----

%(CHANGES)s
""" % read(
    "README", "CHANGES"
)


def get_version(pkg):
    path = os.path.join(os.path.dirname(__file__), pkg, "__init__.py")
    with open(path) as fh:
        m = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]', fh.read(), re.M)
    if m:
        return m.group(1)
    raise RuntimeError("Unable to find __version__ string in %s." % path)


# print(find_packages(exclude=['showcase', 'docs']))

setup(
    name="django-listing",
    version=get_version("django_listing"),
    description="Library for creating HTML listing / table / data grid",
    long_description=long_description,
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 4.0",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="table, datatable, listing, data grid",
    url="https://github.com/elapouya/django-listing",
    author="Eric Lapouyade",
    author_email="elapouya@gmail.com",
    license="GPLv3+",
    packages=find_packages(exclude=["showcase", "docs"]),
    include_package_data=True,
    install_requires=["django>=2", "tablib"],
    extras_require={
        "docs": ["Sphinx", "sphinxcontrib-napoleon"],
    },
    zip_safe=False,
)
