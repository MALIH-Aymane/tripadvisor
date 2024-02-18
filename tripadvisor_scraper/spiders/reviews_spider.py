import random
import time
from typing import Any, Iterable
import scrapy
import os
from scrapy import signals
from tripadvisor_scraper.items import ReviewItem
import pandas as pd
import tqdm

from twisted.internet.error import DNSLookupError, TimeoutError, TCPTimedOutError

class ReviewsSpider(scrapy.Spider):
    name = 'reviews'
    allowed_domains = ['tripadvisor.com']  # Adaptez cela au domaine que vous ciblez
    pages_scraped = 0  # Compteur pour le nombre de pages scrapées

    def __init__(self, *args, **kwargs):
        super(ReviewsSpider, self).__init__(*args, **kwargs)
        self.random_page_limit = random.randint(5, 10) 
        hotels_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'hotels.csv'))
        base_url = "https://www.tripadvisor.com"
        hotels_df['full_hotel_url'] = hotels_df['hotel_url'].apply(lambda x: base_url + x)
        self.hotel_urls = hotels_df['full_hotel_url'].tolist()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(ReviewsSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.handle_error, signal=signals.spider_error)
        return spider 

    def start_requests(self) -> Iterable[scrapy.Request]:
        for hotel in tqdm.tqdm(self.hotel_urls[100:101]):
            yield scrapy.Request(url=hotel, callback=self.parse)

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
            self.random_page_limit = random.randint(1, 5)  # Définir un nouveau nombre aléatoire de pages
            sleep_time = random.randint(8, 17)  # Temps de pause aléatoire entre 10 et 20 secondes
            self.logger.info(f'Pause pour {sleep_time} secondes.')
            time.sleep(sleep_time)  # Pause bloquante
            
        reviews = response.css('div[data-test-target="HR_CC_CARD"]')
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
            divs_with_reviewid = response.xpath('//div[@data-reviewid]')
            # Si aucun élément n'est trouvé, sautez le traitement
            if not divs_with_reviewid:
                continue
            item = ReviewItem()
            item['source_url'] = response.url
            # Extract data with error handling for missing values
            try:
                item['rate'] = review.css('div[data-test-target="review-rating"] span::attr(class)').get(default='r')
                if item['rate'] == 'r':
                    item['rate'] = review.css('div[data-test-target="review-rating"] svg.UctUV.d.H0::attr(aria-label)').get().split()[0]
            except AttributeError:
                item['rate'] = None

            item['review_title'] = ' '.join(review.css('div[data-test-target="review-title"] *::text').getall()).strip()


            #item['review_text'] = review.css('span[data-automation^="reviewText_"].orRIx.Ci._a.C::text').get(default='t').strip()
            #if item['review_text'] == 't':
            #    item['review_text'] = review.css('span.QewHA.H4._a[data-test-target="review-text"] span::text').get(default='t').strip()
            #    if item['review_text'] == 't':
            #        item['review_text'] = ''.join(review.css('div[data-test-target="review-text"]').xpath('.//text()').getall()).strip()
            #        if len(item['review_text']) < 10:
            #           item['review_text'] = ''.join(review.css('span[data-test-target="review-text"]').xpath('.//text()').getall()).strip()
            # Extract all review texts using your preferred selector
            review_texts = response.xpath("//div[@class='_T FKffI bmUTE']//div[@class='fIrGe _T']//span//text()").getall()

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
                item['writing_date'] = review.css('div.cRVSd span::text').getall()
            except AttributeError:
                item['writing_date'] = []

            item['writer'] = review.css('div.ScwkD._Z.o.S4.H3.Ci span a.MjDLG.VKCbE::text').get(default='Anonymous').strip()
            item['writer_link'] = review.css('div.sCZGP a::attr(href)').get()
            item['trip_type'] = review.css('span.hHMDb._R.Me::text').get(default='No Trip Type').strip()
            item['writer_informations'] = review.css('div.tFTbB span::text').getall()
        
            try:
                item['writer_contributions'] = review.css('span.phMBo .yRNgz::text').getall()[0].strip()
            except IndexError:
                item['writer_contributions'] = None

            item['writer_location'] = review.css('span.RdTWF .LXUOn.small::text').get(default='Unknown').strip()
            
            try:
                item['writer_helpfulvotes'] = review.css('span.phMBo .yRNgz::text').getall()[1].strip()
            except IndexError:
                item['writer_helpfulvotes'] = None

            yield item
        next_page = response.css('.ui_pagination.is-centered a.ui_button.nav.next::attr(href)').get()
        self.logger.info(f'next page : {next_page}')
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)
        pass
