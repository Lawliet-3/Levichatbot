from setuptools import setup, find_packages

setup(
    name="levis-chatbot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pandas",
        "python-dotenv",
        "playwright",
        "beautifulsoup4",
        "selenium",
        "webdriver-manager",
        "plotly",
        # other dependencies...
    ],
) 