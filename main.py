
"""
This project is a web scraper designed for scraping GPU information from various online retailers. It focuses on fetching and parsing GPU data based on user preferences.

Key Components:
- Fetcher Class: Utilizes threading with SeleniumBase to concurrently navigate and scrape selected websites for a user-specified GPU model. It requests and gathers the HTML page sources from each site.
- Parser Class: Employs a multiprocessing pool to parse the HTML content using BeautifulSoup. It processes the data to provide the user with organized lists of GPUs, sorted by price and other relevant characteristics.

"""

import fetcher
import parser


def main():
    gpu, allow_used_cards = get_user_input()

    fetch = fetcher.Fetcher(gpu, allow_used_cards)
    fetch.main()

    parse = parser.Parser(fetch.pages, gpu)
    parse.main()

def get_user_input():
    while True:
        gpu = input("What GPU model number are you searching for?\n")
        if not gpu.isdigit():
            print("\nPlease enter a valid model number composed only of digits.")
            continue
        break

    while True:
        allow_used_cards = input("Do you wish do include Refurbished and Open Box cards from Newegg? y/n\n")
        if allow_used_cards != "y" and allow_used_cards != "n":
            print("\nPlease answer with only y or n.")
            continue
        break

    return gpu, allow_used_cards

if __name__ == "__main__":
    main()