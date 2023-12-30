# GPU Web Scraper

## Overview
This Web Scraper is a Python project designed to scrape information about GPUs from various online retailers. It assists users in finding and comparing GPUs prices based on model numbers and characteristics.

The project is educational in nature; its purpose was to learn basic HTML, web scraping and concurrency.  

## Features
- Scrape GPU data from multiple online retailers concurrently.
- Filter search results based on user-specified GPU model numbers and card conditions (new, refurbished, or open-box).
- Employ threading and multiprocessing for efficient data fetching and parsing.
- Sort and display GPU options by price and other relevant characteristics.
- (Tested on Windows only.)

## Requirements
- beautifulsoup4==4.12.2
- seleniumbase==4.21.6
- rich==13.7.0

## Installation
1. Clone the repository to your machine
2. Navigate to the project directory
3. Create a venv: "python -m venv venv"
4. Activate the venv: "venv\Scripts\activate"
5. Install the required packages: "pip install -r requirements.txt"

## Usage:
- Run "main.py"
- Follow the user prompts

## Keywords:
- Threading
- Multiprocessing
- HTML
- Web scraping
- Selenium, SeleniumBase
- BeautifulSoup