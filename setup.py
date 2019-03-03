# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='crown',
    version='0.0.1',
    author='hanwei',
    description='crawler for http://www.pss-system.gov.cn',
    packages=find_packages(where='.', exclude=['crown/store', '*.png', '*.json']),
    install_requires=[
        'requests',
        'wheel',
    ],
    entry_points={
        'console_scripts': [
            'crown = crown.crown:crown',
        ]
    }

)
