import feedparser
import requests
import os
from datetime import datetime, timedelta

# --- 1. 定向追踪源配置 ---
# 官方公告源 + 高权重行业源
OFFICIAL_FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "NVIDIA": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "Google AI": "http://feeds.feedburner.com/blogspot/gJZg",
    "Apple ML": "https://machinelearning.apple.com/rss.xml",
    "The Verge (AI)": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
}

# 马斯克/xAI 专属动态（利用谷歌新闻搜索接口）
MUSK_QUERY = "https://news.google.com/rss/search?q=Elon+Musk+xAI+Tesla+AI+when:1d&hl=en-US&gl=US&ceid=US:en"

# --- 2. 关键词过滤（针对通用源） ---
HOT_COMPANIES = ['NVIDIA', 'OPENAI', 'GOOGLE', 'MUSK', 'XAI', 'TESLA', 'GROK', 'ANTHROPIC', 'CLAUDE', '英伟达', '马斯克']

def fetch_news():
    news_items = []
    seen_links = set()
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    # 遍历官方源
    for source_name, url in OFFICIAL_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if is_recent(entry, yesterday) and entry.link not in seen_links:
                news_items.append(f"[{source_name}] {entry.title}\n{entry.link}")
                seen_links.add(entry.link)

    # 抓取马斯克相关动态
    musk_feed = feedparser.parse(MUSK_QUERY)
    for entry in musk_feed.entries:
        # 在马斯克源中，我们额外检查一下关键词，过滤掉无关的八卦
        text = (entry.title + getattr(entry, 'summary', '')).upper()
        if any(kw in text for kw in ['AI', 'XAI', 'GROK', 'ROBOT', 'CHIP']):
            if is_recent(entry, yesterday) and entry.link not in seen_links:
                news_items.append(f"[Musk/xAI 相关] {entry.title}\n{entry.link}")
                seen_links.add(entry.link)

    return news_items

def is_recent(entry, yesterday):
    """判断文章是否为过去24小时内发布"""
    try:
        pub_time = datetime(*entry.published_parsed[:6])
        return pub_time > yesterday
    except:
        return True # 如果无法解析时间，默认保留（防止漏掉重要新闻）

def send_to_wechat(news_list, sendkey):
    if not news_list:
        print("今日无重要 AI 巨头动态。")
        return
    
    content = "\n\n".join([f"🔥 {item}" for item in news_list])
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🤖 AI 巨头情报 - {datetime.now().strftime('%m月%d日')}",
        "desp": f"### 过去24小时核心大厂动态：\n\n{content}\n\n---\n*由 GitHub Actions 自动筛选推送*"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    key = os.getenv("SERVERCHAN_SENDKEY")
    if key:
        results = fetch_news()
        send_to_wechat(results, key)
    else:
        print("未检测到密钥，请检查 GitHub Secrets。")
