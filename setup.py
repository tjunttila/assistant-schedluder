import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="assistant_scheduler",
    version="2208",
    author="T. Junttila",
    author_email="Tommi.Junttila@aalto.fi",
    description="A tool for scheduling assistants in exercise groups.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tjunttila/assistant-scheduler",
    packages=setuptools.find_packages(),
    license = "MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    setup_requires=['wheel'],
    install_requires=['pyyaml==6.0', 'clingo==5.5.2']
)
