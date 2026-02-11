import feedparser
import requests
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# --- 配置区 ---
FEEDS = {
    # 全球 AI 巨头
    "OpenAI": "https://openai.com/news/rss.xml",
    "NVIDIA": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "Google AI": "http://feeds.feedburner.com/blogspot/gJZg",
    "xAI/Musk": "https://news.google.com/rss/search?q=Elon+Musk+xAI+when:1d&hl=en-US&gl=US&ceid=US:en",
    "Anthropic": "https://news.google.com/rss/search?q=Anthropic+Claude+when:1d&hl=en-US&gl=US&ceid=US:en",
    
    # 中国 AI 资讯
    "36Kr-AI": "https://36kr.com/feed",
    "IT之家-AI": "https://www.ithome.com/rss/"
}

# 中国 AI 关键词
CHINA_KEYWORDS = ['百度', '文心一言', '阿里', '通义千问', '腾讯', '混元', '字节跳动', '豆包', 
                  '华为', '盘古', '智谱', 'Kimi', '月之暗面', 'DeepSeek', '中国', '商汤', 
                  '科大讯飞', '星火', 'MiniMax', '海螺AI']

# 历史数据存储路径
HISTORY_FILE = Path("news_history.json")
HISTORY_DAYS = 90  # 保留90天历史用于对比分析


# --- 核心功能模块 ---

def fetch_news():
    """抓取最新24小时的新闻"""
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
                except:
                    continue
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")
            continue
    
    return news_items


def load_history():
    """加载历史新闻数据"""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # 清理超过保留期的数据
        cutoff_date = datetime.utcnow() - timedelta(days=HISTORY_DAYS)
        history = [
            item for item in history 
            if datetime.fromisoformat(item['timestamp']) > cutoff_date
        ]
        return history
    except:
        return []


def save_history(new_items, history):
    """保存新闻到历史记录"""
    combined = history + new_items
    
    # 去重（基于链接）
    seen = set()
    unique_items = []
    for item in combined:
        if item['link'] not in seen:
            seen.add(item['link'])
            unique_items.append(item)
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_items, f, ensure_ascii=False, indent=2)


def extract_historical_context(history):
    """从历史中提取关键事件用于对比分析"""
    if not history:
        return "无历史数据"
    
    # 按时间倒序排列
    history_sorted = sorted(history, key=lambda x: x['timestamp'], reverse=True)
    
    # 提取过去30天和60-90天的关键新闻（用于跨时空对比）
    now = datetime.utcnow()
    last_30_days = [
        item for item in history_sorted 
        if (now - datetime.fromisoformat(item['timestamp'])).days <= 30
    ]
    
    days_60_90 = [
        item for item in history_sorted 
        if 60 <= (now - datetime.fromisoformat(item['timestamp'])).days <= 90
    ]
    
    context = {
        "recent_30_days": last_30_days[:15],  # 最近30天取15条
        "historical_60_90": days_60_90[:10]   # 2-3个月前取10条
    }
    
    return context


def build_analysis_prompt(news_list, historical_context):
    """构建包含分析框架的Prompt"""
    
    # 今日新闻列表
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
    """调用Gemini进行深度分析"""
    if not news_list:
        return "今日 AI 行业动态较少，暂无重大事件。"
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "错误：未设置 GEMINI_API_KEY"
    
    prompt = build_analysis_prompt(news_list, historical_context)
    
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            error_msg = result.get('error', {}).get('message', '未知错误')
            return f"Gemini 返回异常：{error_msg}"
    
    except Exception as e:
        return f"AI 分析失败：{str(e)}"

import feedparser
import requests
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# --- [此处保留你原有的 FEEDS, CHINA_KEYWORDS, fetch_news, load_history, save_history 逻辑] ---

def generate_web_page(analysis_report):
    """将 Markdown 转换为带样式的 HTML 网页"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 商业内参 - {datetime.now().strftime('%m月%d日')}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
        <style>
            .markdown-body {{ box-sizing: border-box; min-width: 200px; max-width: 980px; margin: 0 auto; padding: 45px; }}
            @media (max-width: 767px) {{ .markdown-body {{ padding: 15px; }} }}
            body {{ background-color: #f6f8fa; }}
        </style>
    </head>
    <body class="markdown-body">
        <p style="text-align: right; color: #666;">更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        {analysis_report} 
    </body>
    </html>
    """
    # 注意：这里为了简单直接放入了 MD。生产环境中建议用 markdown 库转换，
    # 但 GitHub Pages 支持直接渲染 .md 文件，我们可以直接存为 index.md
    with open("index.md", "w", encoding="utf-8") as f:
        f.write(analysis_report)

def send_smart_push(analysis_report, sendkey, username, repo_name):
    """微信只推送摘要和链接，避免截断"""
    # 提取今日核心概括（假设它在第一部分）
    summary_lines = analysis_report.split('\n')
    core_insight = ""
    for line in summary_lines:
        if "今日核心事件" in line or "🌟" in line:
            core_insight = line
            break
            
    web_url = f"https://{username}.github.io/{repo_name}/"
    
    push_content = f"""
### 🌟 今日核心洞察
{core_insight if core_insight else "AI 行业深度变革进行中..."}

---
💡 **由于内容较长，深度分析（二阶效应、中美对比、PM决策建议）已同步至个人情报站：**

🔗 [点击查看完整深度研报]({web_url})

---
*Generated by Gemini 2.5 Pro*
    """
    
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {"title": f"🧠 AI 商业内参 - {datetime.now().strftime('%m月%d日')}", "desp": push_content}
    requests.post(url, data=data)

# 修改 main 函数中的调用逻辑
def main():
    # ... 前面的抓取和分析代码保持不变 ...
    news_data = fetch_news()
    history = load_history()
    historical_context = extract_historical_context(history)
    analysis_report = get_gemini_analysis(news_data, historical_context)
    
    # 1. 生成网页文件
    with open("index.md", "w", encoding="utf-8") as f:
        f.write(analysis_report)
    
    # 2. 微信推送（精简版）
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    # 请确保你在 GitHub Secrets 里设置了这两个变量，或者手动填入
    username = "annieyangyt" 
    repo_name = "ai-news" 
    send_smart_push(analysis_report, sendkey, username, repo_name)
    
    # 3. 存档
    save_history(news_data, history)

def send_to_wechat(summary, sendkey):
    """发送到微信"""
    if not sendkey:
        print("未设置 SERVERCHAN_SENDKEY，跳过微信推送")
        return
    
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": f"🧠 AI 行业深度简报 - {datetime.now().strftime('%m月%d日')}",
        "desp": f"{summary}\n\n---\n✨ *由 Gemini 2.0 驱动 | 包含历史对比与战略分析*"
    }
    
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            print("✅ 微信推送成功")
        else:
            print(f"⚠️ 微信推送失败：{resp.status_code}")
    except Exception as e:
        print(f"❌ 微信推送异常：{e}")


# --- 主流程 ---

def main():
    print("=" * 50)
    print("🚀 AI 行业深度分析系统启动")
    print("=" * 50)
    
    # 1. 抓取今日新闻
    print("\n📡 正在抓取最新新闻...")
    news_data = fetch_news()
    print(f"✅ 获取到 {len(news_data)} 条新闻")
    
    if not news_data:
        print("⚠️ 今日无新闻，退出")
        return
    
    # 2. 加载历史数据
    print("\n📚 加载历史数据...")
    history = load_history()
    print(f"✅ 历史库中有 {len(history)} 条记录")
    
    # 3. 提取历史上下文
    print("\n🔍 分析历史趋势...")
    historical_context = extract_historical_context(history)
    
    # 4. 调用AI进行深度分析
    print("\n🧠 正在生成深度分析报告（需要30-60秒）...")
    analysis_report = get_gemini_analysis(news_data, historical_context)
    
    # 5. 保存今日数据到历史库
    print("\n💾 保存到历史库...")
    save_history(news_data, history)
    
    # 6. 推送到微信
    print("\n📱 推送到微信...")
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    send_to_wechat(analysis_report, sendkey)
    
    # 7. 本地保存备份
    output_file = f"reports/report_{datetime.now().strftime('%Y%m%d')}.md"
    os.makedirs("reports", exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(analysis_report)
    print(f"✅ 报告已保存到 {output_file}")
    
    print("\n" + "=" * 50)
    print("✨ 分析完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
