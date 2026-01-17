import requests
import time
import json
from datetime import datetime, timedelta
from lxml import etree
import re

BASE_URL = "https://bakusai.com"
LIST_URL = "https://bakusai.com/thr_tl/acode=13/ctrid=1/ctgid=150/bid=2396/p={}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "ja-JP,ja;q=0.9"
}

session = requests.Session()
session.headers.update(HEADERS)

# ========== 请求 ==========
def fetch(url):
    try:
        r = session.get(url, timeout=20)
        r.raise_for_status()
        return r.content  # 返回 bytes，避免 encoding declaration 报错
    except Exception as e:
        print("⚠️ 请求失败：", e)
        return None

# ========== 清洗评论文本 ==========
def clean_comments_text(comments_list):
    all_text = []
    for c in comments_list:
        text = c["content"]
        text = re.sub(r'#\d+\s*[\d/:\s]*', '', text)  # 去掉 #数字、日期
        text = re.sub(r'>>\d+', '', text)             # 去掉引用
        text = text.replace('\r', '').replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            all_text.append(text)
    return '\n'.join(all_text)

# ========== 解析列表页最后回复时间 ==========
def parse_last_reply_time(text):
    text = text.strip()
    now = datetime.now()
    if "時間前" in text:
        h = int(re.search(r'(\d+)時間前', text).group(1))
        return now - timedelta(hours=h)
    elif "分前" in text:
        m = int(re.search(r'(\d+)分前', text).group(1))
        return now - timedelta(minutes=m)
    else:  # 12/11 21:12 形式
        try:
            dt = datetime.strptime(text, "%m/%d %H:%M")
            return dt.replace(year=now.year)
        except:
            return None

# ========== 解析列表页 ==========
def parse_thread_list(page, current_year, current_month):
    print(f"📄 正在抓列表页 {page}")
    html = fetch(LIST_URL.format(page))
    if not html:
        return [], True

    tree = etree.HTML(html)
    threads = []
    stop = False

    for li in tree.xpath("//li[@data-tid]"):
        tid = li.get("data-tid")
        title = "".join(li.xpath(".//a[contains(@class,'thr_status_icon')]//text()")).strip()

        # 列表页真实评论数
        comment_count_text = li.xpath(".//span[contains(@class,'comment_count_area')]/span[last()]/text()")
        try:
            comment_count = int(comment_count_text[0].strip())
        except:
            comment_count = 0

        # 最后一条回复时间
        last_reply_text = "".join(li.xpath(".//span[@class='thr-posted-ago']//text()")).strip()
        last_reply_time = parse_last_reply_time(last_reply_text)
        if not last_reply_time:
            continue

        # 停止条件：最后回复不是当月
        if last_reply_time.year != current_year or last_reply_time.month != current_month:
            stop = True
            continue

        if comment_count == 0:
            continue

        threads.append({
            "tid": tid,
            "title": title,
            "url": f"{BASE_URL}/thr_res/acode=13/ctrid=1/ctgid=150/bid=2396/tid={tid}/tp=1/",
            "comment_count": comment_count
        })

    print(f"    ✔ 本页解析到 {len(threads)} 个本月有回复帖子")
    return threads, stop

# ========== 解析帖子页 ==========
def parse_thread_detail(thread):
    html = fetch(thread["url"])
    if not html:
        return None

    tree = etree.HTML(html)

    # 发帖时间
    post_time_text = tree.xpath("//span[@class='posts' and @itemprop='datePublished']/text()")
    if post_time_text:
        post_time_text = post_time_text[0].strip()
        try:
            post_time = datetime.strptime(post_time_text, "%Y/%m/%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        except:
            post_time = ""
    else:
        post_time = ""

    # 帖子正文
    body = "".join(tree.xpath("//div[@id='threadBody']//text()")).strip()

    # 评论
    comments = []
    for idx, res in enumerate(tree.xpath("//div[contains(@class,'resbody')]")):
        if idx >= 100:  # 最多抓 100 条评论
            break
        content = "".join(res.xpath(".//text()")).strip()
        if content:
            comments.append({"content": content})

    comments_text = clean_comments_text(comments)

    return {
        "url": thread["url"],
        "title": thread["title"],
        "comment_count": thread["comment_count"],
        "post_time": post_time,
        "body": body,
        "comments": comments_text
    }

# ========== 主流程 ==========
def crawl_current_month(max_pages=50):
    results = []
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    for page in range(1, max_pages + 1):
        threads, stop = parse_thread_list(page, current_year, current_month)
        for t in threads:
            detail = parse_thread_detail(t)
            if not detail:
                continue
            results.append(detail)
            print(f"    ✅ 收录帖子 {t['tid']}（评论数: {t['comment_count']}）")
            time.sleep(1)

        if stop:
            print("📌 已到当月最后回复帖子，停止翻页")
            break
        time.sleep(2)

    return results

# ========== 入口 ==========
if __name__ == "__main__":
    data = crawl_current_month(max_pages=50)

    with open("bakusai_current_month.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 完成：共抓取 {len(data)} 条本月帖子")
