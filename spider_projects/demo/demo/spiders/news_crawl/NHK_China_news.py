import scrapy
import json


class NhkChinaNewsSpider(scrapy.Spider):
    name = "nhk_china_news"
    allowed_domains = ["news.web.nhk"]

    start_urls = [
        "https://news.web.nhk/newsweb/api/news-nwa-topic-nationwide-0001595.json"
    ]

    def parse(self, response):
        data = json.loads(response.text)

        # 新闻列表
        for item in data.get("items", []):
            url = item.get("url")
            if url:
                yield scrapy.Request(
                    url,
                    callback=self.parse_detail,
                    meta={
                        "title": item.get("title"),
                        "date": item.get("pubDate")
                    }
                )

        # 翻页（非常关键）
        next_url = data.get("next")
        if next_url:
            yield scrapy.Request(next_url, callback=self.parse)

    def parse_detail(self, response):
        title = response.meta.get("title")
        date = response.meta.get("date")

        paragraphs = response.css(
            'div._1i1d7sh0 p._1i1d7sh2::text'
        ).getall()

        content = "\n".join(
            p.strip() for p in paragraphs if p.strip()
        )

        if content:
            yield {
                "url": response.url,
                "title": title,
                "date": date,
                "content": content
            }
