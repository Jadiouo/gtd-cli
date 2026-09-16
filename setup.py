from setuptools import setup, find_packages

setup(
    name="gtd-task-manager",
    version="2.0.0",
    packages=find_packages(),
    install_requires=["click==8.1.7"],
    entry_points={
        "console_scripts": [
            "gtd=v2.main:cli",
        ],
    },
)
