import setuptools

long_description = """
# PlayQuick

"""

setuptools.setup(
    name="PlayQuick", # Replace with your own username
    version="0.1.0a",
    install_requires=[
        "numpy",
        "Pygments",
        "rich",
        "pydub",
    ],
    entry_points={
        'console_scripts': [
            'playquick=commandline:main',
            'pq=commandline:main'
        ],
    },
    author="beatbox4108",
    author_email="68136638+beatbox4108@users.noreply.github.com",
    description="PlayQuick is a Simple media player that has UI and works on a console.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    
)