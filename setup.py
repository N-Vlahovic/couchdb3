import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="CouchDB3",
    version="1.2.0",
    author="Nikolai Vlahovic",
    author_email="nikolai@nexup.com",
    description="A wrapper around the CouchDB API.",
    install_requires=[
        "requests"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/n-vlahovic/couchdb3",
    project_urls={
        "Bug Tracker": "https://github.com/n-vlahovic/couchdb3/issues",
        "Contributing": "https://github.com/N-Vlahovic/couchdb3/blob/master/contributing.md",
        "Documentation": "https://n-vlahovic.github.io/couchdb3/"
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.7",
)
