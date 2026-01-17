import json
from tqdm import tqdm
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
import os

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# 文件路径
INPUT_FILE = "forum_crawl/bakusai_current_month.json"
OUTPUT_FILE = "bakusai_current_month_translated.json"

# 加载 M2M100 模型
model_name = "facebook/m2m100_418M"
tokenizer = M2M100Tokenizer.from_pretrained(model_name)
model = M2M100ForConditionalGeneration.from_pretrained(model_name)

def translate_text(text: str) -> str:
    """单条文本翻译 日文->中文"""
    if not text.strip():
        return ""
    tokenizer.src_lang = "ja"
    encoded = tokenizer(text, return_tensors="pt", truncation=True)
    generated_tokens = model.generate(
        **encoded,
        forced_bos_token_id=tokenizer.get_lang_id("zh"),
        max_new_tokens=512
    )
    zh_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
    return zh_text

def translate_comments(comments_list):
    """翻译评论列表，每条评论单独处理"""
    translated = []
    for c in comments_list:
        if isinstance(c, dict):
            content = c.get("content", "")
            zh = translate_text(content)
            translated.append({
                "content": content,
                "content_zh": zh
            })
        else:
            zh = translate_text(str(c))
            translated.append({
                "content": str(c),
                "content_zh": zh
            })
    return translated

# 读取 JSON
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# 遍历每个帖子，翻译正文和评论
for post in tqdm(data, desc="Translating posts"):
    # 翻译正文
    body = post.get("body", "")
    post["body_zh"] = translate_text(body)
    # 翻译评论
    post["comments"] = translate_comments(post.get("comments", []))

# 写入新文件
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"🎉 翻译完成，结果已保存到 {OUTPUT_FILE}")
