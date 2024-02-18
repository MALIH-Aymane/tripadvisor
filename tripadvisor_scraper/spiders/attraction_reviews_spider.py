import random
import time
from typing import Any, Iterable
import scrapy
import os
from scrapy import signals
from tripadvisor_scraper.items import AttractionReviewItem
import pandas as pd
import tqdm

from twisted.internet.error import DNSLookupError, TimeoutError, TCPTimedOutError

class AttractionReviewsSpider(scrapy.Spider):
    name = 'attractionsreviews'
    allowed_domains = ['tripadvisor.com']  # Adaptez cela au domaine que vous ciblez
    pages_scraped = 0  # Compteur pour le nombre de pages scrapées

    def __init__(self, *args, **kwargs):
        super(AttractionReviewsSpider, self).__init__(*args, **kwargs)
        self.random_page_limit = random.randint(5, 10) 
        attractions_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'attractions.csv'))
        base_url = "https://www.tripadvisor.com"
        attractions_df['full_attraction_url'] = attractions_df['attraction_url'].apply(lambda x: base_url + x)
        self.attraction_urls = attractions_df['full_attraction_url'].tolist()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(AttractionReviewsSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.handle_error, signal=signals.spider_error)
        return spider 

    def start_requests(self) -> Iterable[scrapy.Request]:
        for attraction in tqdm.tqdm(self.attraction_urls):
            yield scrapy.Request(url=attraction, callback=self.parse)

    def handle_error(self, failure, response, spider):
        # Log et sauvegarde des URL qui ont conduit à une erreur
        self.log_failure(response.url)

    def log_failure(self, url):
        # Log qu'aucune review ou erreur n'a été trouvée pour l'URL
        self.logger.info(f'Échec du chargement pour l\'URL : {url}')
        # Écrire l'URL dans un fichier texte
        with open('urls_echouees.txt', 'a') as file:
            file.write(url + '\n')

    def parse(self, response):
        self.pages_scraped += 1
        if self.pages_scraped >= self.random_page_limit:
            self.pages_scraped = 0  # Réinitialiser le compteur
            self.random_page_limit = random.randint(8, 15)  # Définir un nouveau nombre aléatoire de pages
            sleep_time = random.randint(1, 10)  # Temps de pause aléatoire entre 10 et 20 secondes
            self.logger.info(f'Pause pour {sleep_time} secondes.')
            time.sleep(sleep_time)  # Pause bloquante
        
        reviews_section = response.css('section[id="REVIEWS"]')
        if not reviews_section:
            reviews_section = response.css('#tab-data-qa-reviews-0')
        else:
            reviews_section = reviews_section[0]
        reviews = reviews_section.css('div[data-automation="reviewCard"]')
        self.logger.info(f'Nombre de reviews trouvées : {len(reviews)}')
        if len(reviews) == 0:
            # Loggez qu'aucune review n'a été trouvée
            self.logger.info(f'Aucune review trouvée pour l\'URL : {response.url}')
            # Écrire l'URL dans un fichier texte
            with open('urls_echouees.txt', 'a') as file:
                file.write(response.url + '\n')
        # Sauvegarde de la réponse HTML dans un fichier
        filename = 'response.html'
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log(f'Sauvegardé la réponse HTML dans {filename}')            
        
        for review in reviews:
            item = AttractionReviewItem()
            item['source_url'] = response.url
            # Extract data with error handling for missing values
            # Extract data with error handling for missing values
            try:
                item['rate'] = review.css('div[class="jVDab o W f u w JqMhy"]::attr(aria-label)').get(default='r').split()[0]
                if item['rate'] == 'r':
                    item['rate'] = review.css('svg.UctUV.d.H0::attr(aria-label)').get().split()[0]
            except AttributeError:
                item['rate'] = None

            item['review_title'] = ' '.join(review.css('div.biGQs._P.fiohW.qWPrE.ncFvv.fOtGX a[class="BMQDV _F Gv wSSLS SwZTJ FGwzt ukgoS"] *::text').getall()).strip()


            review_texts = review.xpath("div[@class='_T FKffI bmUTE']//div[@class='biGQs _P pZUbB KxBGd']//span//text()").getall()

            # Check if review_texts contains any text
            if review_texts:
                # Join all extracted texts into a single string with a space or any other delimiter you prefer
                item['review_text'] = ' '.join([text.strip() for text in review_texts])
            else:
                # Fallback logic in case no texts were extracted with the primary method
                review_text = response.css('span[data-automation^="reviewText_"].orRIx.Ci._a.C::text').get(default='')

                if not review_text:
                    review_text = response.css('span.QewHA.H4._a[data-test-target="review-text"]::text').get(default='')

                if not review_text:
                    review_text = ''.join(response.css('div[data-test-target="review-text"]').xpath('.//text()').getall()).strip()

                if not review_text or len(review_text) < 10:  # Check for meaningful extraction
                    review_text = ''.join(response.css('span[data-test-target="review-text"]').xpath('.//text()').getall()).strip()

                item['review_text'] = review_text

            try:
                item['writing_date'] = review.css('div.TreSq div.biGQs._P.pZUbB.ncFvv.osNWb::text').getall()
            except AttributeError:
                item['writing_date'] = []

            item['writer'] = review.css('div.mwPje.f.M.k  div.XExLl.f.u.o  div.zpDvc.Zb span  a::text').get(default='Not detected').strip()
            item['writer_link'] = review.css('div.sCZGP a::attr(href)').get()
            item['stay_info'] = review.css('div.RpeCd::text').get(default='No Trip Type').strip()
            item['writer_informations'] = review.css('div.mwPje.f.M.k div.XExLl.f.u.o div.zpDvc.Zb div div span::text').getall()
             
            yield item
        next_page = response.css('#tab-data-qa-reviews-0 > div > div.LbPSX > div > div:nth-child(11) > div:nth-child(2) > div > div.OvVFl.j > div.xkSty > div > a::attr(href)').get()
        self.logger.info(f'next page : {next_page}')
        if next_page is not None:
            yield response.follow("https://www.tripadvisor.com" + next_page, callback=self.parse)
        pass
