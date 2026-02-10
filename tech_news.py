import feedparser
import requests
import os
import json
from datetime import datetime, timedelta

# --- 保持不变的配置部分 ---
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

CHINA_KEYWORDS = ['百度', '文心一言', '阿里', '通义千问', '腾讯', '混元', '字节跳动', '豆包', '华为', '盘古', '智谱', 'Kimi', '月之暗面', 'DeepSeek', '中国']

def fetch_news():
    news_items = []
    seen_links = set()
    yesterday = datetime.utcnow() - timedelta(days=1)

    for source_name, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
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

# --- 升级：深度商业分析引擎 ---
def get_pm_insight_report(news_list):
    if not news_list:
        return "今日 AI 行业动态相对平静，建议复盘历史长线信号。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    context_text = ""
    for idx, item in enumerate(news_list):
        context_text += f"{idx+1}. 来源：{item['source']} | 标题：{item['title']} | 链接：{item['link']}\n"
    
    # 采用 Gemini 2.5 Flash 确保逻辑推理的深度与速度
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # 资深 PM 的 Prompt 建模
    prompt = f"""你是一名拥有敏锐商业化思维的资深 AI 产品经理。
    请根据以下过去 24 小时的全球及中国 AI 资讯数据，撰写一份【AI 商业化决策内参】：
    
    {context_text}
    
    请严格按以下维度进行深度分析：
    
    ### 🌟 今日核心洞察
    (用一句话点破今日最重磅事件背后的商业逻辑)

    ### 🧠 二阶效应分析 (Second-Order Effects)
    (分析这件事发生后，谁会受损？谁会意外获利？比如马斯克 SpaceX 与 xAI 的合并对算力市场的影响。)

    ### 📍 行业坐标：颠覆 vs 迭代
    - **性质判定**：这是颠覆性的技术革命，还是大厂的常规小修小补？
    - **信号过滤**：这是影响未来 3-5 年的长线信号，还是仅仅为拉抬股价的短期公关噪音？

    ### ⚔️ 跨空对比：中美双哨站
    - **跨时空对比**：关联相关巨头 3 个月前的动作（例如马斯克的伏笔是否在今日闭环？）。
    - **中美对比**：对比国内（智谱/Kimi/DeepSeek）与国外（OpenAI/Claude）在同一路径上的身位差异及商业门槛。

    ### 💼 如果你是【产品经理】
    (请给同行提供 2-3 条具体的战略建议：是该调整技术栈？还是出现了新的高价值变现赛道？)

    ---
    **附：精选资讯原文**
    (精选 3 条最值得研读的新闻：[标题](URL))
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "分析模块响应异常，请检查配置。"
    except Exception as e:
        return f"AI 秘书分析失败：{str(e)}"

def send_to_wechat(summary, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"💡 AI 商业内参 - {datetime.now().strftime('%m月%d日')}",
        "desp": f"{summary}\n\n---\n*由 Gemini 2.5 深度驱动 | 商业化决策支持*"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    news_data = fetch_news()
    summary = get_pm_insight_report(news_data)
    send_to_wechat(summary, sendkey)
