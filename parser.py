import re
import multiprocessing as mp
from rich.console import Console


class Parser():
    def __init__(self, pages, gpu):
        self.pages = pages
        self.gpu = gpu

        self.in_stock_gpus = []
        self.all_gpus = []

        self.console = Console()

    # The self.pages queue stores HTML page source; .get() waits indefinitely
    # for a page to appear in the queue, therefore an END signal is necessary
    # Each pool process returns an AsyncResult object containing return 
    # values, exception propagation, etc. 
    def main(self):
        self.result_objects = []
        with mp.Pool(3) as pool:
            while True:
                page = self.pages.get()
                if page == "END":
                    break

                worker = Parser.Worker(self.gpu)
                self.result_objects.append(pool.apply_async(worker.main, args=(page, )))
            
            # To avoid closing the pool prematurely after breaking
            for result in self.result_objects:
                result.wait()

        self.filter_by_stock_status()
        if self.all_gpus:
            self.sort_by_price()
        else:
            print("\nSorry, try again.")
        print("\nShutting down hanging threads...")

    # Users are offered two lists of GPUs, hence the filtering
    def filter_by_stock_status(self):
        for result_object in self.result_objects:
            #try block: to avoid calling .get() on None
            #"if not result": in case of an empty list
            try:
                result = result_object.get(timeout=10)
                if not result:
                    continue

                for attributes in result:
                    if attributes[4] != "Out of Stock":
                        self.in_stock_gpus.append(attributes)
                    self.all_gpus.append(attributes)

            except Exception:
                print("Error while processing parsed data. Search results will be impacted.")

    def sort_by_price(self):
        # x[0] is the GPU price
        self.in_stock_gpus.sort(key=lambda x: x[0])
        self.all_gpus.sort(key=lambda x: x[0])

        gpus = [self.in_stock_gpus, self.all_gpus]
        messages = ["\nIn stock GPUs (see website conditions on stock availability):", "All GPUs:"]

        for gpu_list, message in zip(gpus, messages):
            print(message)

            for index, (price, url, gddr, ti_status, stock_status, newness) in enumerate(gpu_list[:10]):
                ti = " Ti" if ti_status else ""
                newness = "" if newness == "New" else f", {newness}"
                website = "PC-Canada" if "canada" in url else "MemoryExpress" if "memory" in url else "Newegg"
                gddr = re.search("\d+", gddr)[0] + " GB"

                if "All" in message:
                    self.console.print(f"No {index + 1}: {price}, {gddr}{ti}, [link={url}]{website}[/link], {stock_status}{newness}")
                else:
                    self.console.print(f"No {index + 1}: {price}, {gddr}{ti}, [link={url}]{website}[/link]{newness}")

    # Made the Worker methods into a child class because the multiprocesses
    # couldn't pickle/serialize the Parser class instance properly. Could have # been achieved with static methods, but would require too much passing.
    class Worker:
        def __init__(self, gpu):
            self.gpu = gpu

        def main(self, page):
            try:
                page_content = page[0]
                page_url = page[1]
                self.website = self.determine_filters(page_url)

                # items are HTML elements containing information (price, GDDR, # etc.) about each search result on the page
                items = page_content.find_all(class_=self.items_filter)
                if not items:
                    print(f"{self.website} doesn't have this GPU.")
                    return

                page_attributes = []
                for item in items:
                    attributes = self.parsing(item)
                    if attributes is not None:
                        page_attributes.append(attributes)
                
                return page_attributes

            except Exception:
                website = getattr(self, 'website', 'website')
                print(f"An error occured during parsing; {website} HTML was likely modified. Search results will be impacted.")

        def determine_filters(self, page_url):
            self.newness_filter = "item-open-box-italic"
            if "canada" in page_url:
                self.items_filter = "position-relative d-flex flex-column h-full p-1rem border"
                self.url_filter = "d-flex justify-content-center"
                self.price_filter = "mb-0 mt-0.5rem text-red-500 fw-bolder fs-2xl text-center"
                self.in_stock_filter = "position-relative mt-0.875rem"
                self.description_filter = "GridDescription-Clamped mb-0 fs-xs"

                return "https://www.pc-canada.com/"
            elif "memory" in page_url:
                self.items_filter = "c-shca-list-item"
                self.url_filter = "c-shca-list-item__body-main"
                self.price_filter = "c-shca-list-item__price-listed"
                self.description_filter = "c-shca-list-item__body-main"

                return "https://www.memoryexpress.com/"
            elif "newegg" in page_url:
                self.items_filter = "item-cell"
                self.description_filter = "item-title"
                self.url_filter = "a" # it's the first <a> tag in "item"
                self.price_filter = "price-current"
                self.in_stock_filter = "item-promo" #if class is found, item is out of stock

                return "https://www.newegg.ca/"

        # Before parsing, we verify if the URL contains the GPU model; if not,
        # we're on a page with nonpertinent results
        def parsing(self, item):
            #newegg has full links, not just product links
            if "newegg" in self.website:
                url = item.find("a")["href"]
            else:
                url = self.website + item.find('a', class_=self.url_filter)['href']

            # memoryexpress doesn't have the GPU in its url and only returns
            # pertinent results anyway
            if self.gpu in url or "memory" in url:
                attributes = self.parse_gpu_attributes(item, url)
                if None not in attributes:
                    return attributes
            
        def parse_gpu_attributes(self, item, url):
            item_description = item.find(class_=self.description_filter).text

            ti_status = True if re.search("TI", item_description, re.IGNORECASE) else False

            price = self.price_attribute(item, url)
            gddr = self.gddr_attribute(item_description)
            stock_status = self.stock_attribute(item)
            newness = self.newness_attribute(item)

            return (price, url, gddr, ti_status, stock_status, newness)
        
        def price_attribute(self, item, url):
            price = re.search("\$?\d+\.\d+", item.find(class_=self.price_filter).text.strip())
            price = price[0] if price else None
            if "newegg" in url:
                price = "$" + item.find(class_=self.price_filter).strong.text + ".99"

            return price
        
        def gddr_attribute(self, item_description):
            gddr_match = re.search(r"\b\d{1,2}\s?GB?\b", item_description, re.IGNORECASE)
            gddr = gddr_match[0] if gddr_match else "No GDDR information available"

            return gddr

        def stock_attribute(self, item):
            if "canada" in self.website:
                stock_status = item.find('div', class_=self.in_stock_filter).p.text 
            elif "newegg" in self.website:
                stock_status = "Out of Stock" if item.find(class_=self.in_stock_filter) else "In stock"
            # memoryexpress online store is always in stock    
            else:
                stock_status = "In stock"
            
            return stock_status

        def newness_attribute(self, item):
            newness_tag = item.find(class_=self.newness_filter)
            newness = newness_tag.text if newness_tag and newness_tag.text else "New"

            return newness