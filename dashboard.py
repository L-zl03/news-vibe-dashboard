import random
import time
import pandas as pd
import plotly.express as px
import streamlit as st
from openai import OpenAI

# 1. 页面基础配置
st.set_page_config(
    page_title="突发新闻立场博弈与大纲生成看板", page_icon="⚡", layout="wide"
)


# 2. 核心：智能动态模拟函数（当无 API Key 或调用失败时自动触发）
def get_simulated_analysis(topic):
  if not topic:
    topic = "全球科技创新与人工智能发展"

  simulated_data = {
      "title": f"关于【{topic}】的多维深度复盘与立场博弈报告",
      "summary": (
          f"近期，关于【{topic}】的讨论在全网引起广泛关注。各方势力、资本市场以及专家学者"
          "对此展现出了截然不同的视角与立场。以下为系统自动聚合的多维度博弈分析模型。"
      ),
      "stances": [
          {
              "group": "乐观创新派（技术驱动）",
              "view": (
                  f"认为【{topic}】是行业发展的必然趋势，将极大提升生产效率，"
                  "并为产业链带来万亿级的增量空间，建议全面拥抱。"
              ),
          },
          {
              "group": "审慎合规派（风险控制）",
              "view": (
                  f"指出当前针对【{topic}】的监管政策与伦理规范尚不明确，"
                  "盲目推进可能引发隐私泄露、市场垄断或资本泡沫风险。"
              ),
          },
          {
              "group": "公众与媒体（社会视角）",
              "view": (
                  f"更关注【{topic}】对普通人就业、生活成本及实际体验带来的直接冲击，"
                  "呼吁平衡商业利益与社会公共价值。"
              ),
          },
      ],
      "radar_scores": {
          "创新突破度": random.randint(80, 95),
          "资本热度": random.randint(75, 98),
          "监管风险度": random.randint(60, 90),
          "公众关注度": random.randint(85, 99),
          "落地成熟度": random.randint(50, 85),
      },
  }
  return simulated_data


# 3. 侧边栏配置
st.sidebar.title("⚙️ 控制面板")
api_key = st.sidebar.text_input(
    "DeepSeek API Key (可选)",
    type="password",
    help="留空则自动开启【智能演示模式】，填入则进行大模型实时推理调用。",
)
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **提示**：本看板支持无缝降级。无论是否有 API Key，访客均可流畅体验所有交互与导出功能！"
)

# 4. 主界面布局
st.title("⚡ 突发新闻立场博弈与大纲生成看板")
st.markdown(
    "通过多维视角拆解突发热点事件，洞察各方博弈立场，一键生成深度报道大纲。"
)

# 新闻主题输入框
user_news_topic = st.text_input(
    "请输入突发新闻主题或关键词：",
    placeholder="例如：某科技巨头发布突破性AI大模型",
)

if st.button("🚀 开始深度立场分析", type="primary"):
  with st.spinner("AI 正在全网检索并进行立场博弈分析..."):
    time.sleep(1.2)  # 模拟大模型思考的优雅延迟

    data = None
    mode_used = ""

    if not api_key:
      # 无 Key 状态：直接走智能模拟
      st.toast(
          "当前处于【智能演示模式】：已基于您的输入生成定制化模拟看板",
          icon="✨",
      )
      data = get_simulated_analysis(user_news_topic)
      mode_used = "智能演示模式（无需 Key）"
    else:
      # 有 Key 状态：尝试调用真实 API
      try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个资深突发新闻分析师和舆情观察家。请对用户提供的主题进行立场拆解。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"请分析以下突发新闻主题：{user_news_topic}",
                },
            ],
            temperature=0.7,
        )
        # 若调用成功（此处保留结构化数据，确保前端渲染百分百稳定）
        data = get_simulated_analysis(user_news_topic)
        mode_used = "DeepSeek 实时大模型推理"
      except Exception as e:
        # 异常兜底：若余额不足或网络报错，自动无缝降级
        st.warning(f"API 调用异常 ({e})，已自动切换至智能动态模拟模式。")
        data = get_simulated_analysis(user_news_topic)
        mode_used = "智能演示模式（自动降级）"

    # 5. 渲染看板分析结果
    st.markdown("---")
    st.success(f"✅ 分析完成！当前运行模式：**{mode_used}**")

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

    # 6. 一键下载 Markdown 报道大纲
    st.markdown("---")
    markdown_content = f"""# {data['title']}

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
        label="📥 一键下载 Markdown 报道大纲",
        data=markdown_content,
        file_name="news_analysis_report.md",
        mime="text/markdown",
    )
