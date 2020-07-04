import time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import numpy as np
import os
import pandas as pd
import requests
import glob
import reverse_req


class yandex_img_scraper():


    def __init__(self, headless=False, loadimages=False):
        self.headless = headless
        self.loadimages = loadimages
        self.driver = self.get_driver()
        self.driver.set_window_position(0, 0)
        self.driver.set_window_size(700, 1024)


    def resume_from_csv(self, path_to_csv):
        """Resume scraping a search term from a given list of urls already gathered"""
        links = pd.read_csv(path_to_csv)
        print(f'{len(links.index)} links loaded - resuming from {len(links.index) + 1}')
        return len(links.index)

    def get_driver(self):
        # initialize options
        # make browser not load images

        self.options = webdriver.ChromeOptions()
        if not self.loadimages:
            self.prefs = {"profile.managed_default_content_settings.images": 2}
            self.options.add_experimental_option("prefs", self.prefs)
        # hide or show the browser
        if self.headless:
            self.options.add_argument('headless')
        # initialize driver
        return webdriver.Chrome(ChromeDriverManager().install(), options=self.options)

    def wait_until_load_by_xpath(self, xpath):
        #function that will wait until an element loads and time out after 30s
        x = 0
        while x < 300:
            try:
                if self.driver.find_element_by_xpath(xpath):
                    break
            except NoSuchElementException:
                time.sleep(0.1)
                x += 1
        if x == 300:
            raise Exception(f'Element not found, browser timed out\n {xpath}')

    def scroll_down(self, scroll_pause_time=0.01, max_imgs=200, timeout=10):
        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        links_length = 0
        last_links_length = -1
        scroll_loc = 1000
        start = time.time()
        while links_length < max_imgs:
            last_links_length = links_length
            cur_time = time.time() - start
            if cur_time > timeout:
                break
            else:
                # Scroll down to bottom
                self.driver.execute_script(f"window.scrollTo(0, {scroll_loc});")
                scroll_loc += 1000

                # Wait to load page
                time.sleep(scroll_pause_time)

                #get no of imgs
                links = self.driver.find_elements_by_xpath("//a[@class='serp-item__link']")
                links_length = len(links)
                if last_links_length != links_length:
                    start = time.time()
                print(f'\rScrolling... {scroll_loc} / {links_length} / {cur_time} / {timeout}', end='')

    def reverse_img_search(self, to_search='', images=100, size='large', out_dir=f'yandex_reverse_img_search', download_imgs=False):

        def reverse_img_search_single(_to_search='', images=10, size='large', list_id=1):
            url = f'https://yandex.com/images/search?url={_to_search}&rpt=imageview'
            self.driver.get(url)
            try:
                print('clicking more similar link')
                more_similar = self.driver.find_element_by_xpath("//li[@class='cbir-similar__thumb']/a")
                more_similar_link = more_similar.get_attribute("href")
                self.driver.get(more_similar_link)
            except NoSuchElementException as e:
                print('No similar images found')
                return
            size_adj = self.driver.current_url
            size_adj += f'&isize={size}'
            self.driver.get(size_adj)
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE)
            actions.perform()
            print('Scrolling down page until max images reached')
            self.scroll_down(max_imgs=int(images + (images * 0.2)))

            try:
                cookie_button = self.driver.find_element_by_xpath("//button[@class='lg-cc__button lg-cc__button_type_action']")
                cookie_button.click()
            except:
                pass

            #   find all links to images
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE)
            actions.perform()
            print('Finding links from xpath')
            links = self.driver.find_elements_by_xpath("//a[@class='serp-item__link']")

            #   for each link:
            #       click, open image, save, close
            img_urls = []
            failed = 0

            self.driver.execute_script(f"window.scrollTo(0, 0);")
            self.driver.execute_script(f"window.scrollTo(0, 0);")

            print('Gathering links from yandex results...')
            links = links[int(images*0.2):int(images + (images*0.2))]

            for counter, item in enumerate(links):
                print(f'\rGathered {counter + 1}/{len(links)} links', end='')
                # try:
                self.wait_until_load_by_xpath("//div[@class='MMViewerButtons MMViewerButtons_view_default']")
                retries = 0
                while retries < 10:
                    try:
                        item.click()
                        break
                    except ElementClickInterceptedException as e:
                        print('Item click intercepted - waiting 0.1s and trying again')
                        print(e)
                        time.sleep(0.1)
                        retries += 1
                try:
                    button = self.driver.find_element_by_xpath(
                        "//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage']")
                except:
                    try:
                        button = self.driver.find_element_by_xpath(
                            "//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage MMViewerButtons-OpenImage_isOtherSizesEnabled']")
                    except:
                        continue
                img_url = button.get_attribute("href")
                if img_url[:-1] == self.driver.current_url:
                    retries = 0
                    while retries < 10:
                        try:
                            button.click()
                            break
                        except ElementClickInterceptedException as e:
                            print('Button click intercepted - waiting 0.5s and trying again')
                            time.sleep(0.5)
                            retries += 1
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ESCAPE)
                    actions.perform()
                    try:
                        button = self.driver.find_element_by_xpath(
                            "//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage']")
                    except:
                        try:
                            button = self.driver.find_element_by_xpath(
                                "//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage MMViewerButtons-OpenImage_isOtherSizesEnabled']")
                        except:
                            continue
                    img_url = button.get_attribute("href")
                img_urls.append(img_url)
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE)
                actions.perform()


            print(f'Failed to get links for {failed} images')

            print('Done gathering links \n')

            def download_image(img_url, save_name, e=False):
                # Make the actual request, set the timeout for no data to 10 seconds and enable streaming responses so we don't have to keep the large files in memory
                try:
                    request = requests.get(img_url, timeout=10, stream=False)
                    # Open the output file and make sure we write in binary mode
                    start = time.time()
                    print(img_url)
                    if e:
                        to_open = f"{out_dir}/e_{save_name}.jpg"
                    else:
                        to_open = f"{out_dir}/{save_name}.jpg"
                    with open(to_open, 'wb') as fh:
                        # Walk through the request response in chunks of 1024 * 1024 bytes, so 1MiB
                        elapsed = 0
                        for chunk in request.iter_content(1024 * 1024):
                            # Write the chunk to the file
                            fh.write(chunk)
                            elapsed = time.time() - start
                            if elapsed > 10:
                                raise Exception('Time out error')
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    print(f'SSL Error for {img_url} - moving to next')
                    print(e)

            if download_imgs:
                for counter, url in enumerate(img_urls):
                    try:
                        download_image(url, save_name=f'{counter:05}')
                    except:
                        print(f'Downloading failed for {url} - moving to next')
            return img_urls

        if isinstance(to_search, list):
            all_urls = []
            for counter, item in enumerate(to_search):
                urls = reverse_img_search_single(_to_search=item, images=images, size=size, list_id=counter)
                if urls is None:
                    pass
                else:
                    all_urls += urls
        else:
            all_urls = reverse_img_search_single(_to_search=to_search, images=images, size=size)

        return all_urls

        #to search should either be 1) a url 2) path to image on pc 3) list of urls/paths

    def scrape(self, search_term='', images=100, size='large', expander=0, save_urls=True, resume_from=None,
               download=True, random_wait=None):

        #   load results page
        self.driver.get(
            f'https://yandex.com/images/search?text={search_term}&isize={size}')
        self.wait_until_load_by_xpath("//a[@class='serp-item__link']")
        self.scroll_down(max_imgs=int(images))

        #   find all links to images
        #TODO: update to beautifulsoup - can i ? need to click
        links = self.driver.find_elements_by_xpath("//a[@class='serp-item__link']")
        links = links[:int(images)]

        if isinstance(resume_from, str):
            resume_from = self.resume_from_csv(resume_from)

        if resume_from is not None:
            links = links[resume_from:]

        #   for each link:
        #       click, open image, save, close
        img_urls = []
        failed = 0

        try:
            cookie_button = self.driver.find_element_by_xpath(
                "//button[@class='lg-cc__button lg-cc__button_type_action']")
            cookie_button.click()
        except:
            pass

        self.driver.execute_script(f"window.scrollTo(0, 0);")
        self.driver.execute_script(f"window.scrollTo(0, 0);")

        print('Gathering links from yandex results...')
        try:
            for counter, item in enumerate(links):
                print(f'\rGathered {counter+1}/{len(links)} links', end='')
                # try:
                if random_wait is not None:
                    rndn = np.random.uniform(0, random_wait)
                self.wait_until_load_by_xpath("//img")
                retries = 0
                while retries < 10:
                    try:
                        item.click()
                        break
                    except ElementClickInterceptedException as e:
                        print('Item click intercepted - waiting 0.5s and trying again')
                        print(e)
                        time.sleep(0.5)
                        retries += 1
                try:
                    button = self.driver.find_element_by_xpath("//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage']")
                except:
                    try:
                        button = self.driver.find_element_by_xpath("//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage MMViewerButtons-OpenImage_isOtherSizesEnabled']")
                    except:
                        print('Button not found, moving on!')
                        continue
                img_url = button.get_attribute("href")
                if img_url[:-1] == self.driver.current_url:
                    time.sleep(0.1)
                    button.click()
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ESCAPE)
                    actions.perform()
                    try:
                        button = self.driver.find_element_by_xpath(
                            "//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage']")
                    except:
                        button = self.driver.find_element_by_xpath(
                            "//a[@class='MMButton MMButton_type_link MMViewerButtons-OpenImage MMViewerButtons-OpenImage_isOtherSizesEnabled']")
                    img_url = button.get_attribute("href")

                img_urls.append(img_url)
                if save_urls:
                    df = pd.DataFrame(data={"url": img_urls})
                    df.to_csv(f"./{search_term}_image_urls.csv", sep=',', index=False)
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE)
                actions.perform()
        except Exception as e:
            print('ERROR WHEN GATHERING LINKS')
            print(e)
            print('Downloading links gathered until now')
            try:
                scrap.close_driver()
            except:
                print('Error closing driver - probably https://stackoverflow.com/questions/53902507/unknown-error-session-deleted-because-of-page-crash-from-unknown-error-cannot/53970825')

        print(f'Failed to get links for {failed} images')
        print('Done gathering links \n')

        out_dir = f'yandex_results_{search_term}'
        try:
            os.mkdir(out_dir)
        except FileExistsError:
            print(f'Directory {out_dir} already exists')

        # if expander > 0:
        #     extra_urls = self.reverse_img_search(to_search=img_urls[:images], images=expander, size='large', out_dir=f'{search_term}_reverse')
        #     img_urls += extra_urls

        def download_image(img_url, e=False):
            # Make the actual request, set the timeout for no data to 10 seconds and enable streaming responses so we don't have to keep the large files in memory
            request = requests.get(img_url, timeout=10, stream=False)
            # Open the output file and make sure we write in binary mode
            start = time.time()
            if e:
                to_open = f"{out_dir}/e_{(counter - failed + 1):05}.jpg"
            else:
                to_open = f"{out_dir}/{(counter - failed + 1):05}.jpg"

            if request.status_code == 200:
                with open(to_open, 'wb') as fh:
                    # Walk through the request response in chunks of 1024 * 1024 bytes, so 1MiB
                    elapsed = 0
                    for chunk in request.iter_content(1024 * 1024):
                        # Write the chunk to the file
                        fh.write(chunk)
                        elapsed = time.time() - start
                        if elapsed > 10:
                            raise Exception('Time out error')

        failed = 0
        unique_urls = list(set(img_urls))
        if save_urls:
            df = pd.DataFrame(data={"url": unique_urls})
            if resume_from is not None:
                df.to_csv(f"./{search_term}_image_urls.csv", sep=',', mode='a', header=False, index=False)
            else:
                df.to_csv(f"./{search_term}_image_urls.csv", sep=',', index=False)
        if download:
            expander_urls = []
            print(f'{len(img_urls) - len(unique_urls)} duplicate urls found\n')
            for counter, item in enumerate(unique_urls):
                if counter < ((images*(expander+1))+failed):
                    print(f'\rDownloading image {counter-failed+1} of {len(unique_urls)}', end='')
                    try:
                        download_image(item)
                    except Exception as e:
                        print(f'\nImage {counter-failed+1} failed: \n {e}')
                        print('\n')
                        failed += 1
                    if expander > 0:
                        extra_urls = self.reverse_img_search(to_search=item, images=expander, size='large',
                                                             out_dir=f'{search_term}_reverse')
                        if extra_urls is not None:
                            expander_urls += extra_urls
                        if save_urls:
                            all_urls = unique_urls + expander_urls
                            df = pd.DataFrame(data={"url": all_urls})
                            if resume_from is not None:
                                df.to_csv(f"./{search_term}_image_urls.csv", sep=',', mode='a', header=False, index=False)
                            else:
                                df.to_csv(f"./{search_term}_image_urls.csv", sep=',', index=False)
                else:
                    break

            unique_expander_urls = list(set(expander_urls))
            if save_urls:
                all_urls = unique_urls + unique_expander_urls
                df = pd.DataFrame(data={"url": all_urls})
                df.to_csv(f"./{search_term}_image_urls.csv", sep=',', index=False)
            for counter, item in enumerate(unique_expander_urls):
                if counter < ((images*(expander+1))+failed):
                    print(f'\rDownloading image {counter-failed+1} of {len(unique_expander_urls)}', end='')
                    try:
                        download_image(item, e=True)
                    except Exception as e:
                        print(f'\nImage {counter-failed+1} failed: \n {e}')
                        print('\n')
                        failed += 1
                else:
                    break

    def close_driver(self):
        self.driver.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_driver()

    #todo:
    #   Save url option
    #   Download images as you go?

def reverse_search_folder(directory='/Volumes/My Passport/Datasets/Battlestations/rev_seeds', images=200):
    #glob all imgs in folder
    try:
        os.mkdir(f'{directory}/out')
    except FileExistsError as e:
        print('Folder already exists!')
        print(e)
    to_scrape = glob.glob(f'{directory}/*.png') + glob.glob(f'{directory}/*.jpg')
    for counter, img in enumerate(to_scrape):
        if counter == 0:
            continue
        #for each image, upload to imgur
        print(f'Scraping img {counter} of {len(to_scrape)}')
        link = reverse_req.upload_image(image_path=img)
        try:
            os.mkdir(f'{directory}/out/{counter:05}')
        except FileExistsError as e:
            print('Folder already exists!')
            print(e)
        #reverse search, download x results
        # l = "https://im0-tub-com.yandex.net/i?id=644d201ae5b29e6fb95931bd9cb84948&n=13&exp=1"
        scrap = yandex_img_scraper(headless=True)
        try:
            scrap.reverse_img_search(to_search=link, images=images, size='large', out_dir=f'{directory}/out/{counter:05}', download_imgs=True)
            scrap.close_driver()
        except Exception as e:
            print(f'{counter} / {img} failed - moving to next')
            print(f'{e}')
            scrap.close_driver()
        #check for duplicates
