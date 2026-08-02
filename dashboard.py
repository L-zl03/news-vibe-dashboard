import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from openai import OpenAI

# 页面基础配置
st.set_page_config(
    page_title="突发新闻：观点碰撞与立场可视化看板",
    page_icon="📊",
    layout="wide"
)

st.title("📊 突发新闻：观点碰撞与立场可视化看板 (DeepSeek 增强版)")
st.markdown("利用 DeepSeek 实时大模型分析突发事件，一键生成多方立场聚类、情绪雷达图与深度报道大纲。")
st.markdown("---")

# 侧边栏：API 配置
st.sidebar.header("⚙️ 生产力配置中心")
api_key = st.sidebar.text_input("输入 DeepSeek API Key", type="password", help="可在 DeepSeek 开放平台获取")
model_choice = st.sidebar.selectbox("选择大模型", ["deepseek-chat", "deepseek-reasoner"])

# 主界面：输入区
st.subheader("📝 输入新闻或舆论场讨论内容")
news_input = st.text_area(
    "请粘贴多篇不同媒体的报道、专家评论或社交媒体讨论文本：",
    height=160,
    placeholder="例如：关于最新某项重大科技政策落地，各方媒体、行业专家及公众展开了激烈讨论..."
)

# 核心功能：点击分析
if st.button("🚀 启动 DeepSeek 深度聚类与立场分析", type="primary"):
    if not news_input.strip():
        st.warning("⚠️ 请先输入或粘贴需要分析的内容！")
    else:
        with st.spinner("AI 正在通过 DeepSeek 深度解析并构建多维观点矩阵..."):
            try:
                if not api_key:
                    raise ValueError("未检测到 API Key，将自动启用智能降级模拟数据。")
                
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                prompt = f"""你是一个专业的新闻舆情分析师和突发报道总编辑。请对以下新闻/讨论内容进行多方立场聚类分析。
请严格以 JSON 格式输出，不要包含任何 markdown 代码块标记，确保格式如下：
{{
    "pros": "支持方的核心论点与代表群体（使用 Markdown 列表格式）",
    "cons": "反对方的质疑点与代表群体（使用 Markdown 列表格式）",
    "neutral": "中立/客观视角与主流智库观点（使用 Markdown 列表格式）",
    "scores": {{"support": 48, "oppose": 32, "neutral": 20}}
}}
分析内容：
{news_input}"""
                
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
                
                content = response.choices[0].message.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                    
                data = json.loads(content)
                st.success("🎉 DeepSeek 分析成功！")
                
            except Exception as e:
                if api_key:
                    st.error(f"API 调用出错 ({e})，已自动切换至高仿真备用数据。")
                else:
                    st.info("💡 提示：当前未输入 API Key，正在展示演示降级数据。输入 Key 即可体验实时大模型分析！")
                
                data = {
                    "pros": "**核心主张：效率提升与红利释放**\n- 显著降低行业整体运营成本。\n- 顺应全球产业迭代升级大趋势。",
                    "cons": "**核心主张：合规风险与短期阵痛**\n- 监管法律边界尚存模糊地带。\n- 传统从业者短期面临转型压力。",
                    "neutral": "**核心主张：审慎观察与规则前置**\n- 强调技术中立，呼吁配套法规跟进。\n- 多数机构目前处于观望测试期。",
                    "scores": {"support": 55, "oppose": 25, "neutral": 20}
                }
            
            st.session_state['analysis_data'] = data

# 如果已有分析结果，渲染看板与可视化
if 'analysis_data' in st.session_state:
    data = st.session_state['analysis_data']
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### ✅ 支持方核心论点")
        st.info(data["pros"])
    
    with col2:
        st.markdown("### ❌ 反对方质疑点")
        st.error(data["cons"])
    
    with col3:
        st.markdown("### ⚖️ 中立 / 数据视角")
        st.warning(data["neutral"])

    st.markdown("---")
    st.subheader("📈 舆论场立场情绪雷达图")
    
    scores = data.get("scores", {"support": 48, "oppose": 32, "neutral": 20})
    categories = ['支持倾向 (Pro)', '反对倾向 (Con)', '中立客观 (Neutral)']
    values = [scores.get("support", 48), scores.get("oppose", 32), scores.get("neutral", 20)]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='声量指数',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=8, color='#ff7f0e')
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=True, ticks='')
        ),
        showlegend=False,
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📥 导出新闻报道大纲")
    
    markdown_text = f"""# 突发新闻深度报道大纲

## 一、 支持方核心论点
{data['pros']}

## 二、 反对方质疑点
{data['cons']}

## 三、 中立 / 数据视角
{data['neutral']}

## 四、 舆论场声量分布数据
- 支持倾向占比: {scores.get('support')}%
- 反对倾向占比: {scores.get('oppose')}%
- 中立客观占比: {scores.get('neutral')}%

---
*本大纲由 Vibe Coding 智能新闻看板自动生成*"""
    
    st.download_button(
        label="📄 一键下载 Markdown 报道大纲文件",
        data=markdown_text,
        file_name="news_analysis_outline.md",
        mime="text/markdown",
        type="primary"
    )
