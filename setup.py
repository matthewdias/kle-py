import setuptools as st

st.setup(
    version="0.0.0",
    name="damsenviet.kle",
    description="A deserializer for KLE formatted json files.",
    keywords="keyboard layout editor serial",
    url="https://github.com/DamSenViet/kle-py",
    download_url="https://github.com/DamSenViet/kle-py/tarball/0.0.0",
    author="DamSenViet",
    license="MIT",
    namespace_packages=['damsenviet'],
    packages=st.find_packages(
        exclude=["tests", "docs", "scripts"]
    ),
    install_requires=[
        "typeguard>=2.10.0",
        "webcolors>=1.11.1",
    ],
    extras_require={
        "test": [
            "matplotlib>=3.1.2",
            "pytest>=6.1.2",
        ],
        "docs": [
            "sphinx>=3.3.1",
            "pydata-sphinx-theme>=0.4.1",
        ]
    },
    python_requires=">=3.5",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
