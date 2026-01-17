import scrapy
from w3lib.html import remove_tags
import re


class BakusaiChinaNewsSpider(scrapy.Spider):
    name = "bakusai_china_news"
    allowed_domains = ["bakusai.com"]

    # 新闻列表页
    start_urls = [
        "https://bakusai.com/areamain/acode=13/ctrid=1/"
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "FEED_EXPORT_ENCODING": "utf-8",
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def parse(self, response):
        """
        列表页解析：
        - 抓新闻链接（ctgid=137）
        """
        self.logger.info(f"当前抓取页面: {response.url}")

        news_links = response.css(
            "a[href^='/thr_res/'][href*='ctgid=137']::attr(href)"
        ).getall()

        self.logger.info(f"✅ 发现新闻链接 {len(news_links)} 条")

        for href in news_links:
            url = response.urljoin(href)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        """
        新闻详情页解析：
        - 提取标题
        - 提取正文（清理制表符、换行和连续空格）
        - 提取评论
        """
        # ---------- 1️⃣ 标题 ----------
        title = response.css("strong[itemprop='headline']::text").get()
        if not title:
            title = response.css("h1::text").get()
        if title:
            title = title.strip()
        else:
            return  # 没标题就不要了

        # ---------- 2️⃣ 正文 ----------
        article_html = response.css("div#threadBody[itemprop='articlebody']").get()
        article_text = ""
        if article_html:
            article_text = remove_tags(article_html)
            # 去掉制表符、换行和连续空格
            article_text = re.sub(r"[\t\r\n]+", " ", article_text)
            article_text = re.sub(r"\s{2,}", " ", article_text)
            article_text = article_text.strip()

        # ---------- 3️⃣ 评论 ----------
        raw_comments = response.css("div.resbody[itemprop='commentText'] ::text").getall()
        comments = []
        for c in raw_comments:
            c = c.strip()
            if not c:
                continue
            if c.startswith(">>") and c[2:].isdigit():
                continue
            if len(c) < 3:
                continue
            comments.append(c)

        # ---------- 4️⃣ 输出 ----------
        yield {
            "url": response.url,
            "title": title,
            "article_text": article_text,
            "comments": comments
        }
