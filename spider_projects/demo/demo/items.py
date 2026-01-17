import scrapy

class DemoItem(scrapy.Item):
    title = scrapy.Field()
    content = scrapy.Field()
    post_date = scrapy.Field()
    url = scrapy.Field()
