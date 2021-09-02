import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="structuralconnectomes-dbkeator",
    version="0.0.1",
    author="David Keator",
    author_email="dbkeator@gmail.com",
    description="A package to compute structural connectomes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbkeator/structuralconnectomes",
    project_urls={
        "Bug Tracker": "https://github.com/dbkeator/structuralconnectomes/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2.0",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
