"""Explicit fictional fixtures; no network requests or invented real-world news."""
from editor_engine import normalize_sources, validate_brief


def demo_bundle(timestamp):
    sources = normalize_sources([
        {"title": "虚构示例｜示例市票价意见稿", "url": "https://example.com/draft",
         "raw_content": "本方案尚在征求意见阶段，未确定实施时间。拟将起步价由2元调整为3元。拟对每月乘车超过40次的乘客提供折扣。"},
        {"title": "虚构示例｜运营方成本说明", "url": "https://example.com/cost",
         "raw_content": "运营方称人工和维护费用增加，具体成本审计报告尚未公开。"},
        {"title": "虚构示例｜媒体转述意见稿", "url": "https://example.com/reprint",
         "content": "拟将起步价由2元调整为3元。报道转述征求意见稿，未开展独立调查。"},
    ], timestamp)
    payload = {
        "title": "虚构示例：票价调整前，哪些证据需要补齐？",
        "summary": "以下是固定的虚构样例，用于体验事实卡片、选题建议与采访清单。征求意见不等于政策已经实施；多条转载不等于独立信源。",
        "method_summary": "本样例没有联网，没有真实新闻或发布日期。文字匹配与人工核查状态可体验，但不能用于报道。",
        "facts": [
            {"id": "F1", "claim": "方案仍处于征求意见阶段，实施日期未确定。", "party": "示例市主管部门", "kind": "事实主张",
             "evidence": [{"source_id": "S1", "quote": "本方案尚在征求意见阶段，未确定实施时间。", "relation": "支持"}],
             "missing_evidence": "正式公告、征求意见截止日期与最终决定。"},
            {"id": "F2", "claim": "意见稿提出起步价由2元调整为3元。", "party": "示例市主管部门、乘客", "kind": "事实主张",
             "evidence": [{"source_id": "S1", "quote": "拟将起步价由2元调整为3元。", "relation": "支持"},
                          {"source_id": "S3", "quote": "拟将起步价由2元调整为3元。", "relation": "支持"}],
             "missing_evidence": "S3转述S1，不是独立验证。还缺代表性线路与不同乘客的实际支出数据。"},
            {"id": "F3", "claim": "运营方称人工和维护费用增加。", "party": "示例运营方", "kind": "当事方表态",
             "evidence": [{"source_id": "S2", "quote": "运营方称人工和维护费用增加，具体成本审计报告尚未公开。", "relation": "支持"}],
             "missing_evidence": "独立审计、财政补贴、附属业务收入和服务质量记录。"},
        ],
        "stances": [
            {"group": "主管部门", "view": "方案内容仍待意见征集与最终决定。", "attribution": "报道概括", "fact_ids": ["F1", "F2"]},
            {"group": "运营方", "view": "提出成本上升的解释，尚缺公开审计支持。", "attribution": "直接表态", "fact_ids": ["F3"]},
            {"group": "通勤乘客", "view": "需通过采访核实支出变化与优惠覆盖，不能代其表态。", "attribution": "分析推断", "fact_ids": ["F2"]},
        ],
        "pitches": [
            {"title": "涨价一元，每月究竟多花多少？", "why_now": "样例未提供日期，尚无已核实的今日新闻钩子。若真实方案正征求意见，可在截止前提供支出测算。",
             "gap": "本轮检索材料中未见不同通勤距离和频次的实际支出对比。", "readers": "高频通勤者、低收入乘客", "angle": "比较短途、中途、长途和不同月乘次的账单，纳入优惠条件。", "fact_ids": ["F1", "F2"]},
            {"title": "成本上涨，账本还缺哪些数据？", "why_now": "尚无已核实的今日新闻钩子；可在审计数据公布时更新。",
             "gap": "本轮检索材料中未见独立成本审计。", "readers": "关心公共财政与交通治理的读者", "angle": "核对成本、补贴、非票收入与服务质量。", "fact_ids": ["F3"]},
        ],
        "interviews": [
            {"target": "主管部门定价负责人", "question": "方案何时定稿？公众意见如何改变最终方案？", "evidence_needed": "正式公告、听证记录与意见采纳说明。", "fact_ids": ["F1"], "priority": "优先"},
            {"target": "运营方财务负责人及独立审计人员", "question": "成本增加由哪些项目构成？补贴与其他收入如何计入？", "evidence_needed": "审计报告、年度账目与成本口径。", "fact_ids": ["F3"], "priority": "优先"},
            {"target": "不同通勤距离及收入水平的乘客", "question": "按您的出行频次，新方案与折扣会改变多少支出？", "evidence_needed": "匿名化出行账单、路线与优惠资格；不能用个案代表所有乘客。", "fact_ids": ["F2"], "priority": "跟进"},
        ],
    }
    brief, issues = validate_brief(payload, sources)
    return brief, sources, issues
