from setuptools import setup, find_packages

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

setup(
    name="astrospec",
    version="0.1.0",
    author="liangchen",
    author_email="lcpcsky@gmail.com",
    description="astronomy spectroheliograph data processing tools",
    url="https://github.com/liangchen-harold/astrospec",
    packages=find_packages(),
    install_requires=parse_requirements('requirements.txt'),
    entry_points = {
        'console_scripts': [
            'ascli = astrospec.cli:main',                  
        ],              
    },
)

