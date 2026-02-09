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
                    news_items.append(f"【{source_name}】{entry.title}")
                    seen_links.add(entry.link)
            except: continue
    return news_items

# --- 2. Gemini 秘书核心：总结新闻 ---
def get_gemini_summary(news_list):
    if not news_list:
        return "今日 AI 巨头们很安静。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    all_titles = "\n".join(news_list)
    
    # --- 关键修改点：将模型升级为 2.5-flash ---
    # 你也可以选择 gemini-3-flash-preview 获取最新一代能力
    model_name = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    prompt = f"你是一个资深的 AI 行业分析师。以下是过去 24 小时内的 AI 动态：\n{all_titles}\n\n请用中文完成：1. 一句话概括今日核心事件。2. 重点资讯摘要（子弹笔记）。"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            error_info = result.get('error', {}).get('message', '未知模型错误')
            return f"⚠️ API 报错: {error_info}\n\n原始情报：\n{all_titles}"
    except Exception as e:
        return f"🚨 请求失败: {str(e)}\n\n原始情报：\n{all_titles}"

# --- 3. 推送 ---
def send_to_wechat(summary, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🤖 Gemini AI 简报 - {datetime.now().strftime('%m月%d日')}",
        "desp": f"{summary}\n\n---\n*由 Gemini 1.5 Flash 智能总结*"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    news = fetch_news()
    summary = get_gemini_summary(news)
    send_to_wechat(summary, sendkey)
