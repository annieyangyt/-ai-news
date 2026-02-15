import feedparser
import requests
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# --- 1. 配置区 ---
FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "NVIDIA": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "Google AI": "http://feeds.feedburner.com/blogspot/gJZg",
    "xAI/Musk": "https://news.google.com/rss/search?q=Elon+Musk+xAI+when:1d&hl=en-US&gl=US&ceid=US:en",
    "Anthropic": "https://news.google.com/rss/search?q=Anthropic+Claude+when:1d&hl=en-US&gl=US&ceid=US:en",
    # 增加更多国内源以保证覆盖
    "36Kr-AI": "https://36kr.com/feed",
    "IT之家-AI": "https://www.ithome.com/rss/",
    "机器之心": "https://www.jiqizhixin.com/rss" 
}

CHINA_KEYWORDS = ['百度', '文心一言', '阿里', '通义千问', '腾讯', '混元', '字节跳动', '豆包', 
                  '华为', '盘古', '智谱', 'Kimi', '月之暗面', 'DeepSeek', '中国', '商汤', 
                  '科大讯飞', '星火', 'MiniMax', '海螺AI', '国产', '自研']

HISTORY_FILE = Path("news_history.json")
HISTORY_DAYS = 90

# --- 2. 核心抓取逻辑优化：强制国内/国外平衡 ---

def fetch_news():
    news_items = []
    seen_links = set()
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    for source_name, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                try:
                    pub_time = datetime(*entry.published_parsed[:6])
                    if pub_time > yesterday and entry.link not in seen_links:
                        title = entry.title
                        # 核心修改：通过关键词自动打标
                        is_china = any(kw in title for kw in CHINA_KEYWORDS) or source_name in ["36Kr-AI", "IT之家-AI", "机器之心"]
                        
                        news_items.append({
                            "source": source_name,
                            "title": title,
                            "link": entry.link,
                            "is_china": is_china,
                            "timestamp": pub_time.isoformat()
                        })
                        seen_links.add(entry.link)
                except: continue
        except: continue
    
    # 按照国内国外分类，确保分析时各有一半，不被全球巨头淹没
    china_news = [n for n in news_items if n['is_china']]
    global_news = [n for n in news_items if not n['is_china']]
    
    # 返回平衡后的列表（前8条国外，前8条国内）
    return global_news[:8] + china_news[:8]

# --- 3. 分析 Prompt 扁平化与精简化 ---

def build_analysis_prompt(news_list):
    news_context = ""
    for idx, item in enumerate(news_list):
        region = "【国内】" if item.get('is_china') else "【全球】"
        news_context += f"{idx+1}. {region} {item['source']}: {item['title']} (URL: {item['link']})\n"
    
    prompt = f"""你是一位极致理性的 AI 行业战略分析师。
请基于以下原始数据，产出扁平化、无废话的商业内参：

{news_context}

---
### 1️⃣ 事实速览层
- **🌟 今日重磅**：用一句话总结今日最值得关注的信号。
- **🌎 全球巨头**：2-3条重点资讯（公司 + 动作 + [原文链接](URL)）。
- **🇨🇳 中国动态**：必须列出2-3条重点资讯，严禁漏掉（公司 + 动作 + [原文链接](URL)）。

### 2️⃣ 战略影响分析
直接分析今日事件对以下方面的具体影响（不要分点过细，直击要害）：
- **对竞争格局的影响**：谁的身位领先了？谁的市场被蚕食了？
- **对技术路线的影响**：证明了哪个方向的正确性或破灭了哪个幻觉？
- **对商业化变现的影响**：出现了什么新的赚钱路径或成本降低机会？

### 3️⃣ 跨时空对比 (Trend Watch)
- **趋势验证**：今日事件印证了过去3个月的哪个预判？
- **中美差异**：针对同一赛道（如Agent），两边目前的动作差异及背后的策略逻辑。

### 4️⃣ 决策建议 (PM & 投资人视角)
- **产品建议**：如果你是产品经理，应该如何调整路线图（Roadmap）或增加什么功能。
- **投资参考**：哪些标的/领域出现了超额收益机会？哪些是明显的PR噪音？
- **技术选型**：CTO应关注哪个框架、模型或工程化工具。

---
## ⚙️ 输出要求：
1. 禁止任何“总之”、“综上所述”等总结性废话。
2. 每一个分析点必须带上具体公司名。
3. 确保中国 AI 内容占分析篇幅的 40% 以上。
"""
    return prompt

# --- 4. 网页生成与推送逻辑 (保持结构，优化样式) ---

def get_gemini_analysis(news_list):
    api_key = os.getenv("GEMINI_API_KEY")
    prompt = build_analysis_prompt(news_list)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.5, "maxOutputTokens": 8192}}
    try:
        response = requests.post(url, json=payload, timeout=60)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"AI 分析失败：{str(e)}"

def generate_web_page(analysis_report):
    try:
        import markdown
        html_body = markdown.markdown(analysis_report, extensions=['extra', 'codehilite'])
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <style>
        body {{ background-color: #f5f7f9; }}
        .markdown-body {{ box-sizing: border-box; max-width: 850px; margin: 0 auto; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #1a3a5a; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; }}
        li {{ margin-bottom: 12px; }} /* 解决排版不散开的问题 */
    </style>
</head>
<body class="markdown-body">
    <p style="text-align: center; color: #666;">{datetime.now().strftime('%Y年%m月%d日')} | 战略内参</p>
    {html_body}
</body>
</html>
"""
        with open("index.html", "w", encoding="utf-8") as f: f.write(html_template)
    except: pass

def send_smart_push(analysis_report, sendkey, username, repo_name):
    """
    高保真提取：将网页版的“事实速览层”排版完整搬运到微信
    优化点：保留缩进、增加行间距、强化重点加粗
    """
    if not sendkey: return

    # 1. 块提取逻辑：精准定位“事实速览层”到下一个分割线之间的内容
    lines = analysis_report.split('\n')
    extracted_content = []
    is_target_section = False

    for line in lines:
        # 定位起始点
        if "1️⃣ 事实速览层" in line:
            is_target_section = True
            continue
        
        if is_target_section:
            # 遇到下一个大章节或分割线则停止
            if "---" in line or "2️⃣" in line or "###" in line:
                break
            
            # 处理每一行的排版
            # 针对全球/中国动态的二级列表增加缩进感
            processed_line = line.replace("- [", "  • **[").replace("] ", "]** ") 
            extracted_content.append(processed_line)

    # 2. 组装内容，增加空行提升视觉呼吸感
    facts_body = "\n\n".join([l for l in extracted_content if l.strip()])
    
    web_url = f"https://{username}.github.io/{repo_name}/"
    
    # 3. 构造最终推送模板（采用 Figure 2 风格的层级排版）
    push_desp = f"""
{facts_body}

---
💡 **想要查看“二阶效应分析”与“决策建议”？**
🔗 [点击阅读全量深度研报]({web_url})

✨ *Generated by Gemini 2.5 Flash*
    """
    
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🧠 AI 商业内参 | {datetime.now().strftime('%m/%d')}",
        "desp": push_desp
    }
    
    try:
        requests.post(url, data=data, timeout=10)
        print("✅ 微信高保真排版推送成功")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

# --- 5. 唯一主流程 (删除第5段行动清单) ---

def main():
    news_data = fetch_news()
    if not news_data: return
    analysis_report = get_gemini_analysis(news_data)
    generate_web_page(analysis_report)
    sk = os.getenv("SERVERCHAN_SENDKEY")
    send_smart_push(analysis_report, sk, "annieyangyt", "-ai-news")

if __name__ == "__main__":
    main()
