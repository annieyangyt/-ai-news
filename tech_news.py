import feedparser
import requests
import time
from datetime import datetime, timedelta

# 配置信息
# 这里使用 IT之家的 RSS 源，你也可以更换为 https://36kr.com/feed
RSS_URL = 'https://www.ithome.com/rss/'
SERVERCHAN_KEY = "" # 通过环境变量获取，不要硬编码在这里

def get_tech_news():
    feed = feedparser.parse(RSS_URL)
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    news_list = []
    for entry in feed.entries:
        # 解析发布时间并转为 UTC
        pub_time = datetime(*entry.published_parsed[:6])
        if pub_time > yesterday:
            title = entry.title
            link = entry.link
            news_list.append(f"- [{title}]({link})")
    
    return "\n".join(news_list)

def send_to_wechat(content, sendkey):
    if not content:
        content = "今日暂无重大科技更新。"
    
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"今日科技早报 - {datetime.now().strftime('%Y-%m-%d')}",
        "desp": f"### 过去24小时资讯总结：\n\n{content}\n\n---\n*推送自 GitHub Actions*"
    }
    res = requests.post(url, data=data)
    print(f"推送结果: {res.text}")

if __name__ == "__main__":
    import os
    key = os.getenv("SERVERCHAN_SENDKEY")
    if key:
        news = get_tech_news()
        send_to_wechat(news, key)
    else:
        print("未找到 SERVERCHAN_SENDKEY，请在 GitHub Secrets 中配置。")
