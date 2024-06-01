from setuptools import setup, find_packages

setup(
    name="astrospec",
    version="0.2.0",
    author="liangchen",
    author_email="lcpcsky@gmail.com",
    description="astronomy spectroheliograph data processing tools",
    url="https://github.com/liangchen-harold/astrospec",
    packages=find_packages(),
    install_requires=[
        "einops~=0.8.0",
        "lsq_ellipse~=2.2.1",
        "matplotlib~=3.6.0",
        "numpy~=1.23.4",
        "opencv_python~=4.6.0.66",
        "scipy~=1.13.0",
        "seaborn~=0.13.2",
        "tqdm~=4.63.0"
    ],
    entry_points = {
        'console_scripts': [
            'ascli = astrospec.cli:main',                  
        ],              
    },
)

