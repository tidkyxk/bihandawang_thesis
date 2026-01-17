import json
import openai
import time

# ========== 配置 ==========
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
 # 替换成你的 OpenAI API Key
INPUT_FILE = "forum_crawl/bakusai_current_month.json"
OUTPUT_FILE = "forum_crawl/bakusai_sentiment.json"
MODEL = "gpt-5-mini"  # 使用 GPT-5-mini 模型
SLEEP_TIME = 1  # 每次请求间隔，避免频率过高

client = openai.api_key

# ========== 读取帖子 ==========
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    posts = json.load(f)

print(f"总帖子数: {len(posts)}")

# ========== 分析情感 ==========
results = []
for idx, post in enumerate(posts, 1):
    text = post["body"]
    if post["comments"]:
        text += "\n" + post["comments"]

    prompt = (
        "你是中文情感分析专家。"
        "请分析下面这段文字的情感倾向（积极、消极、中性），"
        "并给出简短理由，返回 JSON 格式："
        '{"sentiment": "...", "reason": "..."}\n\n文字:\n' + text
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis_text = resp.choices[0].message.content.strip()

        # 尝试解析 JSON，如果模型返回的是 JSON 字符串
        try:
            analysis_json = json.loads(analysis_text)
        except:
            analysis_json = {"sentiment": "未知", "reason": analysis_text}

        results.append({
            "title": post["title"],
            "url": post["url"],
            "comment_count": post["comment_count"],
            "post_time": post.get("post_time", ""),
            "sentiment": analysis_json.get("sentiment", "未知"),
            "reason": analysis_json.get("reason", "")
        })

        print(f"[{idx}/{len(posts)}] 已分析帖子 '{post['title']}' 情感: {analysis_json.get('sentiment', '未知')}")

    except Exception as e:
        print(f"⚠️ 分析失败：帖子 '{post['title']}'，原因：{e}")

    time.sleep(SLEEP_TIME)  # 控制请求频率

# ========== 保存结果 ==========
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n🎉 完成：共分析 {len(results)} 条帖子情感，结果已保存到 {OUTPUT_FILE}")
