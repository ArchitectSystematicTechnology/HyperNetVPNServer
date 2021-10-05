#!/usr/bin/python

from setuptools import setup, find_packages

setup(
    name="float_integration_test",
    version="0.1",
    description="ai3/float integration tests",
    author="Autistici/Inventati",
    author_email="info@autistici.org",
    url="https://git.autistici.org/ai3/float",
    install_requires=["Jinja2",
                      "PyYAML",
                      "dnspython"],
    setup_requires=[],
    zip_safe=True,
    packages=find_packages(),
    entry_points={},
)

