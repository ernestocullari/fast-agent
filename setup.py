from setuptools import setup, find_packages

setup(
    name="fast-agent-mcp",
    version="0.2.28",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "flask",
        "click==8.1.8"
    ],
)
