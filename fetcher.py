import threading
import queue
import multiprocessing as mp
import time

from seleniumbase import Driver
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup

"""
SeleniumBase is a framework for automated browser testing and web scraping.
It improves on SeleniumBase by simplifying syntax, providing built-in
user-agent headers & anti-anti-scraping measures, etc.
Like Selenium, it is not thread safe.
"""

class Fetcher():
    def __init__(self, gpu, allow_used_cards):
        # Note 1: only newegg has refurbished/open-box cards
        # Note 2: only online store cards are fetched
        # Note 3: I try to filter for GPUs only, not accessories, boxes, etc.

        self.allow_used_cards = allow_used_cards
        self.gpu = gpu

        # self.active_threads is shared; need a lock to modify without racing
        self.active_threads = 0
        self.active_threads_lock = threading.Lock()
        
    def main(self):
        self.frontier_initializer()
        self.fetch()

    def frontier_initializer(self):
        pccanada_url = f"https://www.pc-canada.com/s/?query={self.gpu}&productType=Graphic%20Card"

        memoryexpress_url = f"https://www.memoryexpress.com/Category/VideoCards?FilterID=b9021f59-29a3-73a7-59b5-125edab939f2&InventoryType=InStock&Inventory=OnlineStore&Search={self.gpu}&ViewMode=List"

        if self.allow_used_cards == "y":
            newegg_url = f"https://www.newegg.ca/p/pl?N=100007708&SrchInDesc={self.gpu}"
        else:
            newegg_url = f"https://www.newegg.ca/p/pl?N=100007708%204814&SrchInDesc={self.gpu}"        
        
        self.url_frontier = queue.Queue()
        for url in [pccanada_url, memoryexpress_url, newegg_url]:
            self.url_frontier.put(url)

    def fetch(self):
        self.pages = mp.Queue()

        while not self.url_frontier.empty():
            url = self.url_frontier.get()
            
            threading.Thread(target=self.driver_initialization, args=(url,)).start()
            # Sleep is used to avoid driver synchronization issues where the
            # first driver/thread is given multiple URLs. Selenium
            # isn't thread safe.
            time.sleep(1.5)
        
        print("\nWaiting on website responses...")
        threading.Thread(target=self.check_completion).start()

    def driver_initialization(self, url):
        with self.active_threads_lock:
            self.active_threads += 1

        try:
            driver = Driver(uc=True, headless=True)
            if not driver:
                print(f"Driver initialization for {url} failed. Search results will be impacted.")
                return
            driver.open(url)

            self.request(driver)

        except TimeoutException:
            print("Website timed out and may not be reachable. Search results will be impacted.")
        except WebDriverException:
            print("A WebDriverException occurred. Search results will be impacted. Verify your Internet connection.")
        except Exception:
            print("A driver error occured. Search results will be impacted.")

        finally:
            with self.active_threads_lock:
                self.active_threads -= 1
            if driver:
                driver.quit()

    # Each time, we check for a valid "next page" button by calling the
    # goto_next_page method; it returns True by default, which
    # means the while loop iterates only once unless a next page is found
    def request(self, driver):
        page = None
        pagination_over = False

        while pagination_over is False:
            # SeleniumBase sometimes won't wait for memoryexpress JS to load
            # without this
            time.sleep(1)
            try:
                page_source = driver.get_page_source()
                if page_source:
                    page =  BeautifulSoup(page_source, "html.parser")
                    self.pages.put((page, driver.current_url))

                pagination_over = self.goto_next_page(driver.current_url, driver)

            except Exception:
                print("An exception occurred while fetching the page source. Search results will be impacted.")
                break 

    # Uses specific CSS selectors to find the "next page" button;
    # vulnerable to minute server side modifications
    def goto_next_page(self, url, driver):
        try:
            if "canada" in url:
                pagination_selector = ".ais-Pagination-item--nextPage a"
            elif "memory" in url:
                pagination_selector = ".AJAX_List_Pager_Next a"
            elif "newegg" in url:
                pagination_selector = "button[title='Next']:not([disabled])"
            
            final_page_reached = True
            if driver.is_element_present(pagination_selector):
                driver.click(pagination_selector)
                final_page_reached = False
            return final_page_reached

        except Exception:
            print("An exception occured during browser pagination. Additional pages might not appear in the search results.")
            return True
    
    # Determines when all the drivers are closed, i.e. the threads
    # have finished. We put an END signal in the html pages queue to signal
    # the parser main() method's .get() call to stop waiting for more pages 
    def check_completion(self):
        while True:
            with self.active_threads_lock:
                if self.active_threads == 0:
                    self.pages.put("END")
                    break
            print("...")
            # Sleep to prevent busy waiting
            time.sleep(1.5)