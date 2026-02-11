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
    "36Kr-AI": "https://36kr.com/feed",
    "IT之家-AI": "https://www.ithome.com/rss/"
}

CHINA_KEYWORDS = ['百度', '文心一言', '阿里', '通义千问', '腾讯', '混元', '字节跳动', '豆包', 
                  '华为', '盘古', '智谱', 'Kimi', '月之暗面', 'DeepSeek', '中国', '商汤', 
                  '科大讯飞', '星火', 'MiniMax', '海螺AI']

HISTORY_FILE = Path("news_history.json")
HISTORY_DAYS = 90

# --- 2. 核心抓取与历史功能 ---

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
                        news_items.append({
                            "source": source_name,
                            "title": entry.title,
                            "link": entry.link,
                            "summary": getattr(entry, 'summary', ''),
                            "timestamp": pub_time.isoformat()
                        })
                        seen_links.add(entry.link)
                except: continue
        except Exception as e: print(f"Error fetching {source_name}: {e}"); continue
    return news_items

def load_history():
    if not HISTORY_FILE.exists(): return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        cutoff_date = datetime.utcnow() - timedelta(days=HISTORY_DAYS)
        return [item for item in history if datetime.fromisoformat(item['timestamp']) > cutoff_date]
    except: return []

def save_history(new_items, history):
    combined = history + new_items
    seen = set()
    unique_items = []
    for item in combined:
        if item['link'] not in seen:
            seen.add(item['link'])
            unique_items.append(item)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_items, f, ensure_ascii=False, indent=2)

def extract_historical_context(history):
    if not history: return "无历史数据"
    history_sorted = sorted(history, key=lambda x: x['timestamp'], reverse=True)
    now = datetime.utcnow()
    last_30 = [i for i in history_sorted if (now - datetime.fromisoformat(i['timestamp'])).days <= 30]
    days_60_90 = [i for i in history_sorted if 60 <= (now - datetime.fromisoformat(i['timestamp'])).days <= 90]
    return {"recent_30_days": last_30[:15], "historical_60_90": days_60_90[:10]}


def build_analysis_prompt(news_list, historical_context):
    today_news = ""
    for idx, item in enumerate(news_list):
        today_news += f"{idx+1}. 【{item['source']}】{item['title']}\n   链接: {item['link']}\n"
    
    # 历史对比上下文
    recent_context = ""
    if isinstance(historical_context, dict) and historical_context.get("recent_30_days"):
        recent_context = "\n### 过去30天关键事件（用于发现趋势和关联）：\n"
        for item in historical_context["recent_30_days"][:10]:
            days_ago = (datetime.utcnow() - datetime.fromisoformat(item['timestamp'])).days
            recent_context += f"- [{days_ago}天前] {item['source']}: {item['title']}\n"
    
    historical_ref = ""
    if isinstance(historical_context, dict) and historical_context.get("historical_60_90"):
        historical_ref = "\n### 2-3个月前的伏笔事件（用于发现闭环）：\n"
        for item in historical_context["historical_60_90"][:5]:
            days_ago = (datetime.utcnow() - datetime.fromisoformat(item['timestamp'])).days
            historical_ref += f"- [{days_ago}天前] {item['source']}: {item['title']}\n"
    
    prompt = f"""你是一位资深 AI 行业战略分析师，具备深度思考能力。

## 📊 今日原始数据
{today_news}

{recent_context}

{historical_ref}

---

## 🎯 你的分析任务

请按照以下专业框架完成深度分析报告（使用中文，Markdown格式）：

### 1️⃣ 事实速览层
**🌟 今日核心事件**
（用1-2句话概括最重磅的事件）

**🌎 全球AI巨头动态**
- 列出2-3条重点资讯，每条格式：[公司] 事件描述 → [原文链接](URL)

**🇨🇳 中国AI动态**
- 列出2-3条重点资讯，每条格式：[公司] 事件描述 → [原文链接](URL)

---

### 2️⃣ 战略分析层

**🔍 二阶效应分析**
（针对今日最重要的1-2个事件）
- 直接影响：谁会立即受益/受损？
- 间接影响：3个月后，哪些意外的玩家会受到波及？
- 连锁反应：可能触发哪些行业调整？

**📍 行业坐标定位**
- 这件事在AI发展史中的位置：是颠覆性创新（如GPT-3发布）还是渐进式迭代？
- 商业竞争格局影响：是否改变了现有的竞争态势（如开闭源之争、价格战）？
- 打分：技术重要性 _/10 | 商业影响力 _/10 | 长期价值 _/10

**🎯 信号与噪音过滤**
- 🔥 强信号（影响未来3-5年）：识别哪些是长线趋势的证据
- 💨 噪音（短期热点）：哪些只是PR炒作或跟风
- ⏰ 时间判断：建议持续追踪的时间窗口（如"未来2周关注竞品反应"）

---

### 3️⃣ 对比逻辑层

**⏳ 跨时空对比**
- 今日事件与历史数据的关联：有哪些"伏笔在今天闭环"的案例？
  例如：马斯克3个月前提到的某个方向，今天xAI实现了
- 趋势验证：今日事件是否强化了过去30天观察到的某个趋势？

**🌏 中美AI对比**
（如果今日同时有中美相关新闻）
- 技术路径差异：在相同问题上（如多模态、推理能力），两边的解法有何不同？
- 商业策略差异：开源vs闭源，toB vs toC，生态打法的不同
- 进度判断：在某个具体领域（如代码生成、图像生成），谁领先多久？

**🏢 巨头博弈态势**
- 今日的动作是"进攻"还是"防守"？
- 有没有形成"你发布-我24小时内跟进"的攻防节奏？

---

### 4️⃣ 角色化决策建议

**如果你是产品经理**
- 今日信息对产品规划的启示（如：是否要调整roadmap，增加某个功能）
- 需要重点关注的竞品动向
- 可以借鉴的产品策略

**如果你是投资人**
- 估值逻辑变化：今日事件是否影响某类公司的估值模型
- 新出现的投资机会/风险点
- 值得DD的方向

**如果你是技术Leader**
- 技术栈调整建议
- 团队技能缺口提示
- 开源项目/工具推荐

---

### 5️⃣ 行动清单

**本周需要做的3件事**
1. 
2. 
3. 

**下周重点观察**
- 

---

## ⚙️ 输出要求
- 所有链接必须来自今日新闻数据，不要编造
- 分析要基于事实，避免空洞的"可能会"，给出具体的推理路径
- 中美对比部分：仅在今日确实有相关新闻时才写，没有则跳过
- 历史关联：优先寻找"伏笔闭环"的案例，找不到就诚实说"暂无明显历史关联"
"""
    
    return prompt


def get_gemini_analysis(news_list, historical_context):
    # 只取前 10 条最重要的资讯进行深度分析，避免输入过长导致输出被截断
    top_news = news_list[:10] 
    if not top_news: return "今日无重大事件。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    prompt = build_analysis_prompt(top_news, historical_context)
    
    # 使用支持更长输出的模型配置
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {
            "temperature": 0.7, 
            "maxOutputTokens": 8192  # 提升到 8192
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"AI 分析失败：{str(e)}"

# --- 4. 网页生成与推送 (商业化核心) ---

def generate_web_page(analysis_report):
    """
    高级版网页生成：
    1. 自动将 Markdown 渲染为干净的 HTML
    2. 使用“深邃商业蓝”主题
    3. 彻底消除 ### 和 - 符号的视觉残留
    """
    try:
        import markdown # 如果运行报错，请在 workflow 里的 pip install 增加这个库
        
        # 将 AI 生成的 Markdown 转换为真正的 HTML 结构
        # 这会自动把 ### 变成 <h3> 标签，把 - 变成 <li> 标签
        html_body = markdown.markdown(analysis_report, extensions=['extra', 'codehilite'])
        
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 商业内参 | 深度决策支持</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <style>
        /* 自定义极简商业样式 */
        body {{ 
            background-color: #fcfcfc; 
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
        }}
        .markdown-body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 900px;
            margin: 0 auto;
            padding: 60px 45px;
            background: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            border-radius: 8px;
            color: #2c3e50;
            line-height: 1.8;
        }}
        /* 让标题更有质感 */
        .markdown-body h1, .markdown-body h2 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; color: #1a2a3a; }}
        .markdown-body h3 {{ color: #2980b9; margin-top: 2em; }}
        /* 让列表更清爽，去掉多余的边距 */
        .markdown-body ul {{ padding-left: 1.5em; }}
        .markdown-body li {{ margin-bottom: 8px; }}
        /* 响应式适配移动端 */
        @media (max-width: 767px) {{
            .markdown-body {{ padding: 25px 15px; border-radius: 0; }}
        }}
        .report-header {{ text-align: center; margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
        .report-header h4 {{ color: #95a5a6; font-weight: 400; }}
    </style>
</head>
<body>
    <div class="markdown-body">
        <div class="report-header">
            <h1>💡 AI 行业深度决策内参</h1>
            <h4>{datetime.now().strftime('%Y年%m月%d日')} | 资深战略分析师视角</h4>
        </div>
        {html_body}
        <div style="margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; color: #bdc3c7; font-size: 0.9em; text-align: center;">
            此报告由分析师系统自动生成，基于底层逻辑推演，不构成投资建议。
        </div>
    </div>
</body>
</html>
        """
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_template)
        print("✅ 网页文件 index.html 已成功生成（已完成视觉净化）")
    except Exception as e: 
        print(f"❌ 网页生成失败：{e}")

def send_smart_push(analysis_report, sendkey, username, repo_name):
    """精简推送，解决微信截断问题"""
    if not sendkey: return
    
    # 提取核心洞察
    lines = analysis_report.split('\n')
    core_insight = next((l for l in lines if "今日核心事件" in l or "🌟" in l), "AI 行业深度变革进行中...")
    web_url = f"https://{username}.github.io/{repo_name}/"
    
    push_content = f"""
### 🌟 今日核心洞察
{core_insight}

---
💡 **由于内容较长，深度分析（二阶效应、中美对比、决策建议）已同步至情报站：**

🔗 [点击查看完整深度研报]({web_url})

---
✨ *Generated by Gemini 2.5 Flash*
    """
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    requests.post(url, data={"title": f"🧠 AI 商业内参 - {datetime.now().strftime('%m月%d日')}", "desp": push_content}, timeout=10)
    print("✅ 微信精简版推送成功")

# --- 5. 唯一主流程 ---

def main():
    print("=" * 50 + "\n🚀 AI 行业深度分析系统启动\n" + "=" * 50)
    
    # 抓取与历史
    news_data = fetch_news()
    if not news_data: print("⚠️ 今日无新闻，退出"); return
    
    history = load_history()
    historical_context = extract_historical_context(history)
    
    # AI 分析
    print("\n🧠 正在生成深度分析报告...")
    analysis_report = get_gemini_analysis(news_data, historical_context)
    
    # --- 核心产出 ---
    # 1. 生成网页
    generate_web_page(analysis_report)
    
    # 2. 精简推送
    sk = os.getenv("SERVERCHAN_SENDKEY")
    send_smart_push(analysis_report, sk, "annieyangyt", "-ai-news")
    
    # 3. 存档历史
    save_history(news_data, history)
    
    # 4. 本地备份
    output_file = f"reports/report_{datetime.now().strftime('%Y%m%d')}.md"
    os.makedirs("reports", exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(analysis_report)
    print(f"✅ 报告已本地保存至 {output_file}\n" + "=" * 50 + "\n✨ 分析完成！")

if __name__ == "__main__":
    main()
