# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')
setup(
    name='biliwalle',
    version='0.2dev',
    description='Helper functions for the biliwoli project',
    long_description=long_description,
    long_description_content_type='text/markdown', 
    url='https://github.com/lingchen42/biliwalle.git',
    author='Ling Chen',
    author_email='chenlingm31@gmail.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['moviepy >= 2.0.0.dev2',
                       'pandas > 0.11',
                       'PyYAML >= 5.4.1'],
    entry_points={
        'console_scripts': [
            'waveweaver=biliwalle.waveweaver:main',
            'clipcreator=biliwalle.clipcreator:main',
            'biliwalle=biliwalle.biliwalle:main',
        ],
    },
    classifiers=[ 
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
