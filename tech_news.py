import feedparser
import requests
import os
import json
from datetime import datetime, timedelta

# --- 1. 定向追踪源（分为全球和国内） ---
FEEDS = {
    # 全球 AI 巨头
    "OpenAI": "https://openai.com/news/rss.xml",
    "NVIDIA": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "Google AI": "http://feeds.feedburner.com/blogspot/gJZg",
    "xAI/Musk": "https://news.google.com/rss/search?q=Elon+Musk+xAI+when:1d&hl=en-US&gl=US&ceid=US:en",
    
    # 中国 AI 资讯
    "36Kr-AI": "https://36kr.com/feed",
    "IT之家-AI": "https://www.ithome.com/rss/"
}

# 中国 AI 关键词过滤，确保国内版块内容的准确性
CHINA_KEYWORDS = ['百度', '文心一言', '阿里', '通义千问', '腾讯', '混元', '字节跳动', '豆包', '华为', '盘古', '智谱', 'Kimi', '月之暗面', 'DeepSeek', '中国']

def fetch_news():
    news_items = []
    seen_links = set()
    yesterday = datetime.utcnow() - timedelta(days=1)

    for source_name, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                # 处理可能的时间解析问题
                pub_time = datetime(*entry.published_parsed[:6])
                if pub_time > yesterday and entry.link not in seen_links:
                    news_items.append({
                        "source": source_name,
                        "title": entry.title,
                        "link": entry.link,
                        "summary": getattr(entry, 'summary', '')
                    })
                    seen_links.add(entry.link)
            except: continue
    return news_items

# --- 2. Gemini 秘书：分版块带链接总结 ---
def get_gemini_summary(news_list):
    if not news_list:
        return "今日 AI 行业动态较少。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    context_text = ""
    for idx, item in enumerate(news_list):
        context_text += f"{idx+1}. 来源：{item['source']} | 标题：{item['title']} | 链接：{item['link']}\n"
    
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # 强化 Prompt：要求分出“全球巨头”和“中国动态”两个版块
    prompt = f"""你是一个资深的 AI 行业分析师。
    以下是过去 24 小时内的全球及中国 AI 动态数据：
    {context_text}
    
    请按以下严格格式完成总结（使用中文）：
    
    ### 🌟 今日核心概括
    (用一句话总结全球最重磅的 AI 事件)
    
    ### 🌎 全球 AI 巨头动态
    (列出 3 条左右国外巨头的重点资讯，每条末尾附上 [原文链接](URL))
    
    ### 🇨🇳 中国 AI 每日速递
    (重点筛选并列出 3 条左右中国 AI 公司或政策的重点资讯，每条末尾附上 [原文链接](URL))
    
    **要求**：专业、客观，链接必须与资讯一一对应。"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Gemini 返回数据异常，请检查配置。"
    except Exception as e:
        return f"AI 总结失败：{str(e)}"

def send_to_wechat(summary, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🤖 全球+中国 AI 简报 - {datetime.now().strftime('%m月%d日')}",
        "desp": f"{summary}\n\n---\n*由 Gemini 2.5 驱动 | 自动溯源链接*"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    news_data = fetch_news()
    summary = get_gemini_summary(news_data)
    send_to_wechat(summary, sendkey)
