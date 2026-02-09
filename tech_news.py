import feedparser
import requests
import os
import json
from datetime import datetime, timedelta

# --- 1. 定向追踪源 ---
OFFICIAL_FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "NVIDIA": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "Google AI": "http://feeds.feedburner.com/blogspot/gJZg",
    "xAI/Musk": "https://news.google.com/rss/search?q=Elon+Musk+xAI+when:1d&hl=en-US&gl=US&ceid=US:en"
}

def fetch_news():
    news_items = []
    seen_links = set()
    yesterday = datetime.utcnow() - timedelta(days=1)

    for source_name, url in OFFICIAL_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                pub_time = datetime(*entry.published_parsed[:6])
                if pub_time > yesterday and entry.link not in seen_links:
                    # 关键修改：将来源、标题和链接打包成一个结构
                    news_items.append({
                        "source": source_name,
                        "title": entry.title,
                        "link": entry.link
                    })
                    seen_links.add(entry.link)
            except: continue
    return news_items

# --- 2. Gemini 秘书：带链接总结 ---
def get_gemini_summary(news_list):
    if not news_list:
        return "今日 AI 行业动态较少。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    # 构造带链接的上下文
    context_text = ""
    for idx, item in enumerate(news_list):
        context_text += f"{idx+1}. 来源：{item['source']} | 标题：{item['title']} | 链接：{item['link']}\n"
    
    # 2026 年推荐使用 gemini-2.5-flash
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # 修改 Prompt，强制要求带上链接
    prompt = f"""你是一个资深的 AI 行业分析师。
    以下是过去 24 小时内的 AI 动态数据：
    {context_text}
    
    请按以下要求完成总结：
    1. 用一句话概括今日最核心的事件。
    2. 以子弹笔记列出 3-5 条重点资讯。
    3. **特别要求**：每一条资讯摘要后面，请务必紧跟对应的原始新闻链接，使用 Markdown 格式，例如：[原文链接](URL)。
    4. 语言使用中文，保持专业、精炼。"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Gemini 返回数据异常，请检查 API 配置。"
    except Exception as e:
        return f"AI 总结失败：{str(e)}"

def send_to_wechat(summary, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🤖 AI 简报(含原文) - {datetime.now().strftime('%m月%d日')}",
        "desp": f"{summary}\n\n---\n*由 Gemini 2.5 深度分析并链接溯源*"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    news_data = fetch_news()
    summary = get_gemini_summary(news_data)
    send_to_wechat(summary, sendkey)
