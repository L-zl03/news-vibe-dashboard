import json
import random
import time
from duckduckgo_search import DDGS
import pandas as pd
import plotly.express as px
import streamlit as st
from openai import OpenAI

# 1. 页面基础配置
st.set_page_config(
    page_title="AI 智能情报与深度博弈看板", page_icon="🧠", layout="wide"
)


# 2. 核心函数一：联网搜索实时新闻
def search_latest_news(query):
  try:
    with DDGS() as ddgs:
      results = [r for r in ddgs.text(query, max_results=4)]
      if not results:
        return "未找到相关实时新闻，将基于大模型自身知识库进行推演。"
      news_context = ""
      for idx, r in enumerate(results, 1):
        news_context += f"【新闻 {idx}】\n标题: {r.get('title')}\n摘要: {r.get('body')}\n\n"
      return news_context
  except Exception as e:
    return f"联网搜索暂时受限 ({e})，将基于大模型基础知识进行推演。"


# 3. 核心函数二：智能模拟（无 API Key 时的备用带思考方案）
def get_simulated_analysis(topic):
  if not topic:
    topic = "全球科技创新与人工智能发展"
  return {
      "thinking_process": (
          f"【智能演示模式 - 思考链】\n1. 接收到核心主题：{topic}。\n"
          "2. 正在评估全网检索到的多源信息，识别出技术演进、资本热钱与监管合规三条主线。\n"
          "3. 正在对各方利益相关者的核心诉求进行博弈论建模与加权评分。"
      ),
      "title": f"关于【{topic}】的深度情报分析与多维博弈报告",
      "summary": (
          f"近期，关于【{topic}】的讨论在全网引起热烈反响。各方势力在技术突破、"
          "商业化落地与社会伦理之间展开了深度博弈。"
      ),
      "stances": [
          {
              "group": "创新推动派（技术视角）",
              "view": (
                  f"认为【{topic}】代表了新一轮产业革命的方向，能够显著拉动效率，"
                  "具备极高的长期配置价值。"
              ),
          },
          {
              "group": "风险控制派（合规与安全）",
              "view": (
                  f"指出在【{topic}】高速发展背后，数据安全、伦理边界与潜在泡沫不容忽视，"
                  "呼吁建立前置监管框架。"
              ),
          },
          {
              "group": "社会大众（民生视角）",
              "view": (
                  f"更关注【{topic}】对个体就业、实际成本和生活体验的实质性影响，"
                  "强调技术应当兼具普惠性。"
              ),
          },
      ],
      "radar_scores": {
          "创新突破度": random.randint(78, 95),
          "资本热度": range_val := random.randint(75, 98),
          "监管风险度": random.randint(60, 90),
          "公众关注度": random.randint(82, 99),
          "落地成熟度": random.randint(55, 88),
      },
  }


# 4. 侧边栏配置
st.sidebar.title("⚙️ 情报控制台")
api_key = st.sidebar.text_input(
    "DeepSeek API Key",
    type="password",
    help=(
        "输入 Key 后将启动【联网搜索 + 深度思考链推理】；留空则使用演示模式。"
    ),
)
st.sidebar.markdown("---")
st.sidebar.info(
    "🧠 **深度思考引擎**：看板支持 AI 思考过程可视化，直击事件背后的博弈逻辑。"
)

# 5. 主界面布局
st.title("🧠 AI 智能情报与立场博弈看板")
st.markdown(
    "输入任意突发热点，AI 将自动联网、**深度思考并推演**各方博弈立场与综合指标。"
)

user_news_topic = st.text_input(
    "请输入突发新闻主题或关键词：",
    placeholder="例如：人形机器人进入工厂量产 / 某国发布最新 AI 监管法案",
)

if st.button("🚀 开始联网检索与深度思考推演", type="primary"):
  with st.spinner("正在联网检索资讯，AI 正在进行多维逻辑思考与推演中..."):
    search_results_text = search_latest_news(user_news_topic)
    time.sleep(0.8)

    data = None
    mode_used = ""

    if not api_key:
      st.toast("当前处于演示模式", icon="✨")
      data = get_simulated_analysis(user_news_topic)
      mode_used = "智能演示模式（无 API Key）"
    else:
      try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        prompt = f"""
        你是一个资深突发新闻分析师和舆情与博弈论专家。以下是通过网络实时检索到的关于【{user_news_topic}】的最新资讯：
        
        {search_results_text}
        
        请结合上述资讯，执行以下步骤并严格以 JSON 格式输出：
        1. 在 thinking_process 中写出你的深度思考过程：分析这些新闻之间是否存在冲突、各方利益相关者的核心痛点是什么、为什么要这样评估。
        2. 撰写专业严谨的分析报告。
        
        必须严格以 JSON 格式输出，不要包含任何 markdown 符号（如 ```json），直接输出合法的 JSON 字符串，结构如下：
        {{
            "thinking_process": "此处写你对搜索结果的深度逻辑思考与推演分析过程（150字以上）...",
            "title": "针对该事件的专业分析报告标题",
            "summary": "200字左右的综合概述",
            "stances": [
                {{"group": "第一方立场名称（如：技术驱动派）", "view": "该立场的具体观点详细说明"}},
                {{"group": "第二方立场名称（如：合规监管派）", "view": "该立场的具体观点详细说明"}},
                {{"group": "第三方立场名称（如：公众与媒体视角）", "view": "该立场的具体观点详细说明"}}
            ],
            "radar_scores": {{
                "创新突破度": 85,
                "资本热度": 90,
                "监管风险度": 70,
                "公众关注度": 95,
                "落地成熟度": 80
            }}
        }}
        """
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "system",
                "content": (
                    "你是一个资深舆情与博弈分析专家，擅长深度逻辑推演并严格输出 JSON。"
                ),
            }, {
                "role": "user",
                "content": prompt,
            }],
            response_format={"type": "json_object"},
            temperature=0.85,
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        mode_used = "实时联网检索 + DeepSeek 深度思考链推理"

      except Exception as e:
        st.warning(f"API 调用或解析异常 ({e})，已自动降级为演示模式。")
        data = get_simulated_analysis(user_news_topic)
        mode_used = "智能演示模式（降级兜底）"

    # 6. 渲染看板分析结果
    st.markdown("---")
    st.success(f"✅ 深度推演完成！当前运行模式：**{mode_used}**")

    # 🌟 新增：AI 深度思考过程展示面板
    with st.expander("🧠 点击展开：AI 的深度逻辑思考与博弈推演链 (Reasoning)", expanded=True):
      st.info(data.get("thinking_process", "暂无思考链记录。"))

    with st.expander("🔍 查看 AI 联网检索到的原始参考资讯"):
      st.text(search_results_text)

    st.subheader(data["title"])
    st.write(data["summary"])

    # 多方立场观点卡片展示
    st.markdown("### 📌 多方立场深度博弈")
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    for idx, stance in enumerate(data["stances"]):
      with cols[idx]:
        st.info(f"**{stance['group']}**")
        st.write(stance["view"])

    # 综合多维指标雷达图渲染
    st.markdown("---")
    st.markdown("### 📊 综合多维指标评估雷达图")
    scores = data["radar_scores"]
    df_radar = pd.DataFrame(
        dict(r=list(scores.values()), theta=list(scores.keys()))
    )
    fig = px.line_polar(
        df_radar, r="r", theta="theta", line_close=True, range_r=[0, 100]
    )
    fig.update_traces(fill="toself")
    st.plotly_chart(fig, use_container_width=True)

    # 7. 一键下载 Markdown 报道大纲
    st.markdown("---")
    markdown_content = f"""# {data['title']}

## 🧠 AI 深度思考与推演链
{data.get('thinking_process', '')}

## 检索参考资讯
{search_results_text}

## 概述
{data['summary']}

## 核心立场博弈
"""
    for s in data["stances"]:
      markdown_content += f"- **{s['group']}**: {s['view']}\n"

    markdown_content += "\n## 多维指标评分\n"
    for k, v in scores.items():
      markdown_content += f"- {k}: {v}分\n"

    st.download_button(
        label="📥 一键下载完整思考与情报大纲报告",
        data=markdown_content,
        file_name="news_reasoning_report.md",
        mime="text/markdown",
    )
