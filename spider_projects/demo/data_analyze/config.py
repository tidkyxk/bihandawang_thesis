import os
import json
import time
from openai import OpenAI


# ===============================
# 1. 初始化 DeepSeek 客户端
# ===============================
def init_client():
    """初始化客户端，支持多种方式获取API密钥"""
    # 尝试从不同来源获取API密钥
    api_key = None

    # 1. 环境变量
    api_key = os.getenv("DEEPSEEK_API_KEY")

    # 2. 配置文件（如果存在）
    if not api_key:
        try:
            from config_secret import DEEPSEEK_API_KEY
            api_key = DEEPSEEK_API_KEY
        except ImportError:
            pass

    # 3. 用户输入（如果没有配置）
    if not api_key:
        print("=" * 40)
        print("📝 请输入DeepSeek API密钥")
        print("=" * 40)
        api_key = input("API密钥: ").strip()

        # 询问是否保存
        save = input("是否保存到本地配置文件以便下次使用？(y/n): ").lower()
        if save == 'y':
            try:
                with open('config_secret.py', 'w', encoding='utf-8') as f:
                    f.write(f'DEEPSEEK_API_KEY = "{api_key}"\n')
                print("✅ API密钥已保存到 config_secret.py")
            except Exception as e:
                print(f"❌ 保存失败: {e}")

    if not api_key:
        raise ValueError("未提供API密钥")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )


client = init_client()


# ===============================
# 2. 情感分析函数
# ===============================
def analyze_sentiment(text, target_name):
    """
    text: 待分析文本
    target_name: '新闻正文' 或 '新闻评论区'
    返回：dict
    """

    if not text.strip():
        return {
            "sentiment": "中性",
            "reason": "文本内容为空或信息量不足，无法体现明显情感倾向。"
        }

    prompt = f"""
你是一个严格、客观的文本情感分析模型。

请分析以下【{target_name}】的整体情感倾向。

要求：
1. 情感只能是：积极 / 中性 / 消极
2. 根据文本整体语气、用词和表达判断，不进行事实评价
3. 使用简体中文
4. 输出必须是 JSON 格式，仅包含以下字段：
   - sentiment
   - reason

文本如下：
{text}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        result_text = response.choices[0].message.content

        # 解析JSON
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # 如果返回的不是JSON，尝试提取情感
            if "积极" in result_text:
                sentiment = "积极"
            elif "消极" in result_text:
                sentiment = "消极"
            else:
                sentiment = "中性"

            return {
                "sentiment": sentiment,
                "reason": result_text[:200] + "..." if len(result_text) > 200 else result_text
            }

    except Exception as e:
        print(f"⚠️  情感分析失败: {e}")
        return {
            "sentiment": "未知",
            "reason": f"分析过程中出现错误: {str(e)}"
        }


# ===============================
# 3. 分析单条新闻
# ===============================
def analyze_single_news(news_item):
    article_text = news_item.get("article_text", "")
    comments = news_item.get("comments", [])

    # 将评论合并为一段文本
    comment_text = "\n".join([f"[评论{i + 1}] {comment}" for i, comment in enumerate(comments)])

    print(f"🔍 分析新闻: {news_item.get('title', '无标题')[:50]}...")

    article_sentiment = analyze_sentiment(article_text, "新闻正文")
    comment_sentiment = analyze_sentiment(comment_text, "新闻评论区") if comment_text else {
        "sentiment": "无评论",
        "reason": "该新闻暂无用户评论"
    }

    # 计算一致性
    alignment = "一致" if article_sentiment["sentiment"] == comment_sentiment["sentiment"] else "不一致"

    return {
        "url": news_item.get("url", ""),
        "title": news_item.get("title", ""),
        "article_sentiment": article_sentiment,
        "comment_sentiment": comment_sentiment,
        "sentiment_alignment": alignment,
        "total_comments": len(comments)
    }


# ===============================
# 4. 批量分析 JSON 文件
# ===============================
def analyze_news_file(input_path, output_path, sleep_time=1, max_items=None):
    """批量分析新闻"""

    # 检查输入文件
    if not os.path.exists(input_path):
        print(f"❌ 输入文件不存在: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        news_list = json.load(f)

    # 限制分析数量
    if max_items and max_items < len(news_list):
        news_list = news_list[:max_items]
        print(f"📊 将分析前 {max_items} 条新闻（共 {len(news_list)} 条）")

    results = []

    print(f"🚀 开始分析 {len(news_list)} 条新闻...")
    print("=" * 60)

    for idx, news in enumerate(news_list, 1):
        print(f"[{idx}/{len(news_list)}] ", end="")
        try:
            result = analyze_single_news(news)
            results.append(result)

            # 显示简要结果
            print(f"✅ 新闻: {result['article_sentiment']['sentiment']} | "
                  f"评论: {result['comment_sentiment']['sentiment']} | "
                  f"一致性: {result['sentiment_alignment']}")

            time.sleep(sleep_time)  # 防止请求过快
        except Exception as e:
            print(f"❌ 分析失败: {news.get('title', '无标题')} - {e}")
            results.append({
                "error": str(e),
                "url": news.get("url", ""),
                "title": news.get("title", "")
            })

    # 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 生成摘要
    print("\n" + "=" * 60)
    print("📊 分析摘要")
    print("=" * 60)

    successful = sum(1 for r in results if "error" not in r)
    print(f"✅ 成功分析: {successful}/{len(news_list)} 条新闻")

    # 统计情感分布
    article_sentiments = {"积极": 0, "中性": 0, "消极": 0, "无评论": 0, "未知": 0}
    comment_sentiments = {"积极": 0, "中性": 0, "消极": 0, "无评论": 0, "未知": 0}
    alignments = {"一致": 0, "不一致": 0}

    for result in results:
        if "error" in result:
            continue

        article_sent = result["article_sentiment"]["sentiment"]
        comment_sent = result["comment_sentiment"]["sentiment"]
        alignment = result["sentiment_alignment"]

        if article_sent in article_sentiments:
            article_sentiments[article_sent] += 1

        if comment_sent in comment_sentiments:
            comment_sentiments[comment_sent] += 1

        if alignment in alignments:
            alignments[alignment] += 1

    print("\n📰 新闻情感分布:")
    for sent, count in article_sentiments.items():
        if count > 0:
            print(f"  {sent}: {count} 条")

    print("\n💬 评论情感分布:")
    for sent, count in comment_sentiments.items():
        if count > 0:
            print(f"  {sent}: {count} 条")

    print(f"\n🔄 情感一致性: 一致 {alignments['一致']} 条 | 不一致 {alignments['不一致']} 条")

    print(f"\n💾 分析完成，结果已保存至：{output_path}")


# ===============================
# 5. 主程序入口
# ===============================
if __name__ == "__main__":
    import sys

    # 简单命令行参数
    max_items = None
    if len(sys.argv) > 1:
        try:
            max_items = int(sys.argv[1])
            print(f"🔧 限制分析数量: {max_items} 条")
        except ValueError:
            pass

    # 检查配置文件是否存在，给用户提示
    if not os.path.exists("config_secret.py"):
        print("💡 提示：可以创建 config_secret.py 文件保存API密钥")
        print("     内容：DEEPSEEK_API_KEY = 'your_key_here'")
        print("     将此文件添加到 .gitignore 中避免上传\n")

    analyze_news_file(
        input_path="bakusai_china_news.json",
        output_path="deepseek_news_sentiment_result.json",
        sleep_time=1,
        max_items=max_items
    )