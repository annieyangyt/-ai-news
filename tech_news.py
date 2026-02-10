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

# --- 2. 增强型分析大脑（解决超时问题） ---
def get_pm_insight_report(news_list, retries=2):
    if not news_list:
        return "今日 AI 行业动态较少。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    context_text = ""
    for idx, item in enumerate(news_list):
        context_text += f"{idx+1}. 来源：{item['source']} | 标题：{item['title']} | 链接：{item['link']}\n"
    
    # 使用 Gemini 2.5 Flash 处理复杂分析
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    prompt = f"""你是一名资深 AI 产品经理。请分析以下资讯：\n{context_text}\n
    请按以下格式输出商业内参：
    ### 🌟 今日核心洞察
    ### 🧠 二阶效应分析 (谁受损？谁获利？)
    ### 📍 行业坐标 (是颠覆还是迭代？长线信号还是噪音？)
    ### ⚔️ 跨空对比 (中美代差及商业门槛)
    ### 💼 产品经理决策建议
    ---
    **精选原文**：[标题](URL)"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # 循环尝试，防止偶发性超时
    for i in range(retries + 1):
        try:
            # 关键修改：timeout 增加到 120 秒
            response = requests.post(url, json=payload, timeout=120) 
            result = response.json()
            if 'candidates' in result:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"Gemini 返回异常: {result.get('error', {}).get('message', '未知错误')}"
        except requests.exceptions.ReadTimeout:
            if i < retries:
                print(f"请求超时，正在进行第 {i+1} 次重试...")
                time.sleep(5) # 等待 5 秒后再试
                continue
            else:
                return "🚨 AI 秘书连续多次请求超时，可能是今日分析任务过重。请稍后手动重试。"
        except Exception as e:
            return f"分析引擎崩溃：{str(e)}"

def send_to_wechat(summary, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"💡 AI 商业内参 - {datetime.now().strftime('%m月%d日')}",
        "desp": summary
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    sk = os.getenv("SERVERCHAN_SENDKEY")
    news_data = fetch_news()
    summary = get_fx_report = get_pm_insight_report(news_data)
    send_to_wechat(summary, sk)
