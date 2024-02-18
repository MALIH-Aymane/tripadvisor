# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TripadvisorScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class ReviewItem(scrapy.Item):
    rate = scrapy.Field()
    review_title = scrapy.Field()
    review_text = scrapy.Field()
    writing_date = scrapy.Field()
    writer = scrapy.Field()
    writer_link = scrapy.Field()
    writer_location = scrapy.Field()
    writer_contributions = scrapy.Field()
    writer_helpfulvotes = scrapy.Field()
    trip_type = scrapy.Field()
    stay_date = scrapy.Field()
    source_url = scrapy.Field()
    writer_informations = scrapy.Field()


class AttractionReviewItem(scrapy.Item):
    rate = scrapy.Field()
    review_title = scrapy.Field()
    review_text = scrapy.Field()
    writing_date = scrapy.Field()
    writer = scrapy.Field()
    writer_link = scrapy.Field()
    trip_type = scrapy.Field()
    stay_info = scrapy.Field()
    source_url = scrapy.Field()
    writer_informations = scrapy.Field()
