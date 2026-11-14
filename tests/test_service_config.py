import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo_data import demo_bundle
from service_config import ConfigurationError, normalize_api_key

APP = Path(__file__).resolve().parents[1] / "dashboard.py"


class CredentialTests(unittest.TestCase):
    def test_boundary_noise_and_wrapping_quotes_are_removed(self):
        for value in ("  sk-test-value\n", '“ sk-test-value ”', "\ufeff\u200b \u200b‘sk-test-value’\u2060", "`sk-test-value`"):
            self.assertEqual(normalize_api_key(value, "测试密钥"), "sk-test-value")

    def test_internal_non_ascii_and_controls_are_rejected_without_value_disclosure(self):
        for value in ("sk-PRIVATE中文", "sk-PRIVATE\u200bvalue", "sk-PRIVATE value", "sk-PRIVATE\nvalue", "Bearer sk-PRIVATE-value", "sk-PRIVATE\x00value", "sk-PRIVATE'value"):
            with self.assertRaises(ConfigurationError) as error:
                normalize_api_key(value, "测试密钥")
            self.assertNotIn("PRIVATE", str(error.exception))
            self.assertIn("测试密钥", str(error.exception))

    def test_missing_and_non_text_values_have_safe_actionable_errors(self):
        for value in ("", "   ", "\u200b", None, 123):
            with self.assertRaises(ConfigurationError):
                normalize_api_key(value, "云端测试密钥")


class ConnectionInteractionTests(unittest.TestCase):
    def create_app(self):
        app = AppTest.from_file(str(APP), default_timeout=15)
        app.secrets["TAVILY_API_KEY"] = "tvly-test-placeholder"
        app.secrets["DEEPSEEK_API_KEY"] = "test-model-placeholder"
        app.run()
        app.text_input(key="topic").set_value("城市公共交通票价上调")
        return app

    def test_non_ascii_sidebar_key_is_rejected_before_any_network_call(self):
        app = self.create_app()
        app.text_input(key="deepseek_key").set_value("sk-PRIVATE中文")
        with patch("tavily.TavilyClient") as search, patch("openai.OpenAI") as model:
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertIn("侧栏", app.error[0].value)
            self.assertIn("非英文", app.error[0].value)
            self.assertNotIn("PRIVATE", app.error[0].value)
            search.assert_not_called()
            model.assert_not_called()
            self.assertIsNone(app.session_state["brief_bundle"])

    def test_bad_cloud_search_key_is_rejected_before_model_or_search_call(self):
        app = self.create_app()
        app.secrets["TAVILY_API_KEY"] = "tvly-PRIVATE中文"
        with patch("tavily.TavilyClient") as search, patch("openai.OpenAI") as model:
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertIn("TAVILY_API_KEY", app.error[0].value)
            self.assertNotIn("PRIVATE", app.error[0].value)
            search.assert_not_called()
            model.assert_not_called()

    def test_normalized_keys_reach_clients_and_chinese_topic_is_preserved(self):
        app = self.create_app()
        app.text_input(key="deepseek_key").set_value("“ sk-test-model ”")
        app.secrets["TAVILY_API_KEY"] = " tvly-test-search\n"
        brief, sources, _ = demo_bundle("2026-11-14T12:00:00+08:00")
        response = SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=brief.model_dump_json()))])
        with patch("tavily.TavilyClient") as search, patch("openai.OpenAI") as model:
            search.return_value.search.return_value = {"results": [{"title": s.title, "url": s.url, "raw_content": s.text} for s in sources]}
            model.return_value.__enter__.return_value.chat.completions.create.return_value = response
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            search.assert_called_once_with(api_key="tvly-test-search")
            self.assertEqual(model.call_args.kwargs["api_key"], "sk-test-model")
            messages = model.return_value.__enter__.return_value.chat.completions.create.call_args.kwargs["messages"]
            self.assertIn("城市公共交通票价上调", messages[1]["content"])

    def test_remaining_encoding_error_does_not_claim_network_failure_or_leak_value(self):
        app = self.create_app()
        _, sources, _ = demo_bundle("2026-11-14T12:00:00+08:00")
        with patch("tavily.TavilyClient") as search, patch("openai.OpenAI") as model:
            search.return_value.search.return_value = {"results": [{"title": s.title, "url": s.url, "raw_content": s.text} for s in sources]}
            model.return_value.__enter__.return_value.chat.completions.create.side_effect = UnicodeEncodeError("ascii", "PRIVATE中文", 7, 9, "not ASCII")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertIn("请求头编码失败", app.error[0].value)
            self.assertNotIn("PRIVATE", app.error[0].value)
            self.assertNotIn("稍后重试", app.error[0].value)


if __name__ == "__main__":
    unittest.main()
