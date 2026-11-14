import copy
import json
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo_data import demo_bundle
from editor_engine import (
    apply_freshness_guard, export_markdown, normalize_sources,
    publication_date, validate_brief, verification,
)

STAMP = "2026-11-14T12:00:00+08:00"
APP = Path(__file__).resolve().parents[1] / "dashboard.py"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.brief, self.sources, _ = demo_bundle(STAMP)

    def test_fabricated_quote_and_unknown_source_are_removed(self):
        payload = self.brief.model_dump()
        payload["facts"][0]["evidence"][0]["quote"] = "这是一段来源材料中完全不存在的虚构原话。"
        payload["facts"][1]["evidence"][0]["source_id"] = "S999"
        result, issues = validate_brief(payload, self.sources)
        self.assertEqual(result.facts[0].evidence, [])
        self.assertEqual(len(result.facts[1].evidence), 1)
        self.assertEqual(len(issues), 2)
        self.assertEqual(verification(result.facts[1], {}), "未交叉验证")

    def test_duplicate_evidence_cannot_inflate_corroboration(self):
        payload = self.brief.model_dump()
        payload["facts"][0]["evidence"] *= 2
        result, _ = validate_brief(payload, self.sources)
        self.assertEqual(len(result.facts[0].evidence), 1)
        self.assertEqual(verification(result.facts[0], {}), "未交叉验证")

    def test_multiple_reports_need_editor_note_and_independence_confirmation(self):
        fact = self.brief.facts[1]
        self.assertIn("独立性待人工核查", verification(fact, {}))
        self.assertIn("独立性待人工核查", verification(fact, {"F2": {"independent": True}}))
        self.assertIn("编辑已确认", verification(fact, {"F2": {"independent": True, "note": "已核对独立采访记录"}}))

    def test_conflicting_evidence_and_inference_never_marked_verified(self):
        fact = copy.deepcopy(self.brief.facts[1])
        fact.evidence[0].relation = "反驳"
        reviews = {"F2": {"independent": True, "note": "人工备注"}}
        self.assertIn("反驳", verification(fact, reviews))
        fact.evidence[0].relation = "支持"
        fact.kind = "分析推断"
        self.assertIn("分析推断", verification(fact, reviews))

    def test_invalid_fact_references_and_duplicate_ids_fail_closed(self):
        payload = self.brief.model_dump()
        payload["pitches"][0]["fact_ids"] = ["F999"]
        with self.assertRaises(ValueError):
            validate_brief(payload, self.sources)
        payload = self.brief.model_dump()
        payload["facts"][1]["id"] = "F1"
        with self.assertRaises(ValueError):
            validate_brief(payload, self.sources)

    def test_stance_format_variations_are_recovered_conservatively(self):
        payload = self.brief.model_dump()
        payload["stances"] = {
            "group": "运营方", "view": "提出成本增加的解释。",
            "attribution": "根据报道总结", "fact_ids": "F3",
            "source_url": "https://untrusted.example/invented",
        }
        brief, issues = validate_brief(payload, self.sources)
        self.assertEqual(len(brief.stances), 1)
        self.assertEqual(brief.stances[0].fact_ids, ["F3"])
        self.assertEqual(brief.stances[0].attribution, "分析推断")
        self.assertGreaterEqual(len(issues), 3)
        self.assertNotIn("source_url", brief.stances[0].model_dump())
        for attribution in (None, ["直接表态"], {"type": "直接表态"}, 123):
            payload["stances"]["attribution"] = attribution
            brief, issues = validate_brief(payload, self.sources)
            self.assertEqual(brief.stances[0].attribution, "分析推断")

    def test_malformed_or_missing_stances_do_not_discard_core(self):
        for value in (None, "无法分析", [], {"错误字段": "不可识别"}):
            payload = self.brief.model_dump()
            payload["stances"] = value
            brief, issues = validate_brief(payload, self.sources)
            self.assertEqual(brief.stances, [])
            self.assertEqual(brief.facts, self.brief.facts)
            self.assertEqual(brief.pitches, self.brief.pitches)
            self.assertEqual(brief.interviews, self.brief.interviews)
            self.assertTrue(issues)
        payload = self.brief.model_dump()
        del payload["stances"]
        brief, issues = validate_brief(payload, self.sources)
        self.assertEqual(brief.stances, [])
        self.assertTrue(issues)

    def test_invalid_stance_is_skipped_without_inventing_evidence(self):
        payload = self.brief.model_dump()
        payload["stances"] = [
            {"group": "未知方", "view": "无有效依据", "attribution": "直接表态", "fact_ids": ["F999"]},
            {"group": "缺编号", "view": "不可用"},
            "不是对象",
            payload["stances"][0],
        ]
        brief, issues = validate_brief(payload, self.sources)
        self.assertEqual(len(brief.stances), 1)
        self.assertEqual(brief.stances[0], self.brief.stances[0])
        self.assertGreaterEqual(len(issues), 3)

    def test_stance_recovery_does_not_relax_core_validation(self):
        for value in (None, [], "不是JSON对象"):
            with self.assertRaises(ValueError):
                validate_brief(value, self.sources)
        payload = self.brief.model_dump()
        payload["stances"] = None
        payload["facts"][0]["kind"] = "非法类型"
        with self.assertRaises(ValueError):
            validate_brief(payload, self.sources)
        payload = self.brief.model_dump()
        payload["stances"] = "不可用"
        payload["interviews"][0]["fact_ids"] = ["F999"]
        with self.assertRaises(ValueError):
            validate_brief(payload, self.sources)
    def test_source_dates_not_inferred_from_url_or_retrieval(self):
        results = normalize_sources([
            {"title": "页面", "url": "https://example.com/2026/11/14/article", "content": "摘要材料"},
            {"url": "https://example.com/2026/11/14/article#fragment", "content": "重复材料"},
            {"url": "javascript:alert(1)", "content": "非法链接"},
            {"url": "https://user:password@example.com", "content": "含认证信息"},
        ], STAMP)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].published_date, "")
        self.assertEqual(results[0].text_kind, "检索摘要")
        self.assertEqual(publication_date("Thu, 12 Nov 2026 10:00:00 GMT"), "2026-11-12")

    def test_freshness_guard_rejects_unknown_old_and_future_dates(self):
        today = date(2026, 11, 14)
        for value in ("", "2025-01-01", "2026-11-15"):
            brief = copy.deepcopy(self.brief)
            self.sources[0].published_date = value
            apply_freshness_guard(brief, self.sources, today)
            self.assertTrue(brief.pitches[0].why_now.startswith("尚无已核实"))
        brief = copy.deepcopy(self.brief)
        brief.pitches[0].why_now = "近期新进展需人工核查"
        self.sources[0].published_date = "2026-11-12"
        apply_freshness_guard(brief, self.sources, today)
        self.assertEqual(brief.pitches[0].why_now, "近期新进展需人工核查")

    def test_export_keeps_sources_verification_and_all_editor_modules(self):
        meta = dict(mode="体验虚构样例", generated_at=STAMP, audience="编辑", region="未限定", period="近一周", issues=[])
        content = export_markdown(self.brief, self.sources, {"F2": {"note": "转述同一公告，不能视为独立信源"}}, meta)
        for part in ("事实卡片", "来源日期：未提供", "网页正文摘录", "检索摘要摘录", "选题建议", "采访清单", "转述同一公告"):
            self.assertIn(part, content)


class InteractionTests(unittest.TestCase):
    def load_demo(self):
        app = AppTest.from_file(str(APP), default_timeout=15).run()
        self.assertFalse(app.exception)
        app.radio(key="mode").set_value("体验虚构样例").run()
        app.button(key="generate_brief").click().run()
        self.assertFalse(app.exception)
        return app

    def test_demo_renders_all_modules_and_survives_widget_changes(self):
        app = self.load_demo()
        self.assertEqual([x.label for x in app.tabs], ["事实卡片", "选题建议", "采访清单", "采编推进", "多方立场", "来源与方法"])
        original = app.session_state["brief_bundle"]["id"]
        app.text_area[1].set_value("来源转述同一公告，未完成独立验证。").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["brief_bundle"]["id"], original)
        next(b for b in app.button if b.label.startswith("准备下载")).click().run()
        self.assertIn("未完成独立验证", app.session_state["prepared_export"]["markdown"])
        app.run()
        self.assertEqual(app.session_state["brief_bundle"]["id"], original)

    def test_real_mode_empty_input_is_rejected(self):
        app = AppTest.from_file(str(APP)).run()
        app.button(key="generate_brief").click().run()
        self.assertFalse(app.exception)
        self.assertIn("请输入明确", app.error[0].value)
        self.assertIsNone(app.session_state["brief_bundle"])

    def test_mock_real_flow_and_failed_retry_preserve_last_success(self):
        app = AppTest.from_file(str(APP), default_timeout=15)
        app.secrets["TAVILY_API_KEY"] = "test-search-placeholder"
        app.secrets["DEEPSEEK_API_KEY"] = "test-model-placeholder"
        app.run()
        app.text_input(key="topic").set_value("城市公共交通票价上调")
        brief, sources, _ = demo_bundle(STAMP)
        search_result = {"results": [{"title": s.title, "url": s.url, "raw_content": s.text} for s in sources]}
        response = SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=brief.model_dump_json()))])
        with patch("tavily.TavilyClient") as search, patch("openai.OpenAI") as model:
            search.return_value.search.return_value = search_result
            model.return_value.__enter__.return_value.chat.completions.create.return_value = response
            app.button(key="generate_brief").click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(search.call_count, 1)
            original = app.session_state["brief_bundle"]["id"]
            app.run()
            app.checkbox(key="replace_confirm").check()
            model.return_value.__enter__.return_value.chat.completions.create.side_effect = RuntimeError("PRIVATE_UPSTREAM_ERROR")
            app.button(key="generate_brief").click().run()
            self.assertEqual(app.session_state["brief_bundle"]["id"], original)
            self.assertEqual(search.call_count, 1)  # session material cache reused
            self.assertNotIn("PRIVATE_UPSTREAM_ERROR", app.error[0].value)
            auth_error = type("AuthorizationFailure", (Exception,), {"status_code": 401})
            model.return_value.__enter__.return_value.chat.completions.create.side_effect = auth_error("PRIVATE_AUTH_DETAILS")
            app.button(key="generate_brief").click().run()
            self.assertIn("HTTP 401", app.error[0].value)
            self.assertNotIn("PRIVATE_AUTH_DETAILS", app.error[0].value)
            self.assertEqual(app.session_state["brief_bundle"]["id"], original)

    def test_malformed_stances_still_render_and_export_core_results(self):
        app = AppTest.from_file(str(APP), default_timeout=15)
        app.secrets["TAVILY_API_KEY"] = "test-search-placeholder"
        app.secrets["DEEPSEEK_API_KEY"] = "test-model-placeholder"
        app.run()
        app.text_input(key="topic").set_value("公共交通票价")
        brief, sources, _ = demo_bundle(STAMP)
        payload = brief.model_dump()
        payload["stances"] = [{"group": "缺少观点和事实依据"}]
        search_result = {"results": [{"title": s.title, "url": s.url, "raw_content": s.text} for s in sources]}
        response = SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)))])
        with patch("tavily.TavilyClient") as search, patch("openai.OpenAI") as model:
            search.return_value.search.return_value = search_result
            model.return_value.__enter__.return_value.chat.completions.create.return_value = response
            app.button(key="generate_brief").click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            result = app.session_state["brief_bundle"]["brief"]
            self.assertEqual(result.stances, [])
            self.assertEqual(len(result.facts), 3)
            self.assertTrue(app.warning)
            next(b for b in app.button if b.label.startswith("准备下载")).click().run()
            report = app.session_state["prepared_export"]["markdown"]
            for text in ("事实卡片", "选题建议", "采访清单", "本次未取得可用的多方立场"):
                self.assertIn(text, report)
            self.assertEqual(model.return_value.__enter__.return_value.chat.completions.create.call_count, 1)
            self.assertEqual(search.call_count, 1)


if __name__ == "__main__":
    unittest.main()
