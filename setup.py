import pathlib

from setuptools import setup, find_packages

# Read version from file
version_path = pathlib.Path(__file__).parent / "src" / "__version__.py"
version_ns = {}
exec(version_path.read_text(), version_ns)

setup(
    name="netconfparser",
    version=version_ns["__version__"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    description="A Netconf parsing utility",
    author="Netconf parser team",
    author_email="netconf_parser_team@no-reply.com",
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "netconfparser=netconfparser:main"  # update with your actual main
        ]
    },
)