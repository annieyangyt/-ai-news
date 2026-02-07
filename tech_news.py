import feedparser
import requests
from datetime import datetime, timedelta
import os

# --- 核心配置：权威 AI 资讯源 ---
AI_FEEDS = [
    'https://openai.com/news/rss.xml',              # OpenAI 官方公告
    'https://www.theverge.com/ai-artificial-intelligence/rss/index.xml', # The Verge AI 频道
    'https://arstechnica.com/tag/ai/feed/',         # Ars Technica AI 深度报道
    'https://www.technologyreview.com/topic/artificial-intelligence/feed/', # MIT 科技评论
    'https://www.wired.com/category/science/ai/feed/' # Wired AI 专栏
]

# --- 过滤机制：确保内容真的跟 AI 相关 ---
# 只有标题或摘要包含以下词汇的文章才会被选中
KEYWORDS = ['AI', 'GPT', 'LLM', 'OpenAI', 'DeepMind', 'Claude', 'Agent', '模型', '人工智能', '机器人']

def get_filtered_ai_news():
    news_list = []
    seen_links = set() # 用于去重
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    for url in AI_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # 1. 检查发布时间（过去 24 小时）
                pub_time = datetime(*entry.published_parsed[:6])
                if pub_time < yesterday:
                    continue
                
                # 2. 检查去重
                if entry.link in seen_links:
                    continue
                
                # 3. 关键词双重保险过滤
                text_to_check = (entry.title + getattr(entry, 'summary', '')).upper()
                if any(kw.upper() in text_to_check for kw in KEYWORDS):
                    title = entry.title.strip()
                    news_list.append(f"- **{title}**\n  [点击阅读]({entry.link})")
                    seen_links.add(entry.link)
        except Exception as e:
            print(f"解析 {url} 失败: {e}")
            
    return "\n\n".join(news_list)

def send_to_wechat(content, sendkey):
    if not content:
        print("今日无重要 AI 资讯。")
        return
    
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🤖 AI 深度情报 - {datetime.now().strftime('%m月%d日')}",
        "desp": f"### 过去24小时精选 AI 动态：\n\n{content}\n\n---\n*推送自你的私有情报机器人*"
    }
    res = requests.post(url, data=data)
    print(f"推送状态: {res.text}")

if __name__ == "__main__":
    key = os.getenv("SERVERCHAN_SENDKEY")
    if key:
        content = get_filtered_ai_news()
        send_to_wechat(content, key)
    else:
        print("错误：未配置 SERVERCHAN_SENDKEY")
