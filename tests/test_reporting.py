import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from demo_data import demo_bundle
from reporting_workflow import *

STAMP = '2026-11-14T12:00:00+08:00'
QUOTE = '目前只是征求意见，并未确定调整票价。'
APP = Path(__file__).resolve().parents[1] / 'dashboard.py'


def project():
    brief, sources, issues = demo_bundle(STAMP)
    bundle = dict(id='test-project', brief=brief, sources=sources,
                  meta=dict(mode='体验虚构样例', generated_at=STAMP, issues=issues, audience='编辑', region='未限定', period='近一周'))
    ensure_workflow(bundle)
    return bundle, {}


def material(bundle, reviews, **kwargs):
    values = dict(title='虚构采访纪要', speaker='虚构运营方', obtained_date='2026-11-14', text=QUOTE,
                  fact_ids=['F1'], quote=QUOTE, relation='反驳', ai_allowed=False)
    values.update(kwargs)
    return add_material(bundle, reviews, **values)


class ReportingTests(unittest.TestCase):
    def test_new_contradiction_invalidates_review_and_pitch(self):
        b, r = project()
        save_review(b, r, 'F1', '已核实', '已核对原始文件')
        save_decision(b, 'P1', '可推进', '已有证据基础')
        material(b, r)
        self.assertEqual(fact_status(b['brief'].facts[0], r), '待复核')
        self.assertFalse(r['F1']['independent'])
        self.assertEqual(b['workflow'].decisions['P1'].status, '待复核')
        with self.assertRaises(WorkflowError):
            save_review(b, r, 'F1', '已核实', '不能忽略反驳')
        self.assertEqual(b['workflow'].revision, 4)

    def test_claim_edit_demotes_old_evidence_and_tracks_before_after(self):
        b, r = project()
        fact = b['brief'].facts[0]
        old = fact.claim
        edit_fact(b, r, 'F1', '运营方表示方案尚在征求意见。', fact.party, '当事方表态', '正式决策文件', '采访澄清')
        self.assertTrue(all(e.relation == '背景' for e in b['brief'].facts[0].evidence))
        self.assertEqual(b['workflow'].changes[-1].before, old)
        self.assertEqual(fact_status(b['brief'].facts[0], r), '待复核')

    def test_material_is_unverified_dated_and_linked_to_task(self):
        b, r = project()
        mid = material(b, r, task_id='Q1', completed=True)
        source = b['sources'][-1]
        self.assertFalse(source.ai_allowed)
        self.assertEqual(source.published_date, '')
        self.assertEqual(source.obtained_date, '2026-11-14')
        self.assertEqual(b['workflow'].tasks['Q1'].material_ids, [mid])
        self.assertEqual(b['workflow'].tasks['Q1'].status, '已完成')

    def test_quote_and_date_rejected_before_mutating(self):
        for kwargs in [dict(quote='不在材料里的连续摘录内容'), dict(obtained_date='2099-01-01'), dict(task_id='Q999')]:
            b, r = project()
            before = project_bytes(b, r)
            with self.assertRaises(WorkflowError):
                material(b, r, **kwargs)
            self.assertEqual(project_bytes(b, r), before)

    def test_new_fact_can_link_existing_material(self):
        b, r = project()
        mid = material(b, r, fact_ids=[])
        fid = new_fact(b, r, '运营方尚未决定涨价。', '运营方', '当事方表态', '正式决定')
        link_material(b, r, fid, mid, QUOTE, '支持')
        save_review(b, r, fid, '已核实', '回听录音确认当事方表述')
        self.assertEqual(fact_status(b['brief'].facts[-1], r), '已核实')
        self.assertFalse(r[fid]['independent'])

    def test_save_roundtrip_and_corrupt_evidence_rejection(self):
        b, r = project()
        material(b, r)
        save_decision(b, 'P1', '继续补采', '等待主管部门答复')
        raw = project_bytes(b, r)
        loaded, reviews = restore_project(raw)
        self.assertEqual(project_bytes(loaded, reviews), raw)
        content = json.loads(raw)
        content['brief']['facts'][0]['evidence'][0]['quote'] = '伪造的摘录并不出现在原文中。'
        with self.assertRaises(WorkflowError):
            restore_project(json.dumps(content))
        content = json.loads(raw)
        content['sources'][0]['url'] = 'javascript:alert(1)'
        with self.assertRaises(WorkflowError):
            restore_project(json.dumps(content))
        self.assertNotIn('deepseek_key', raw.decode())

    def test_file_limits_and_encoding(self):
        self.assertEqual(read_material_file(QUOTE.encode(), 'memo.md'), QUOTE)
        for content, name in [(b'x' * 262145, 'memo.txt'), (b'abc', 'memo.pdf'), (b'\xff', 'memo.txt')]:
            with self.assertRaises(WorkflowError):
                read_material_file(content, name)

    def test_ai_only_sees_selected_authorized_materials_and_not_notes(self):
        b, r = project()
        first = material(b, r, ai_allowed=True)
        material(b, r, text='保密材料不应发送到模型服务。', quote='', fact_ids=[])
        r['F1'] = Review(note='不应发送的私人核查备注').model_dump()
        prompt = assessment_prompt(b, r, [first])
        self.assertIn(QUOTE, prompt)
        self.assertNotIn('保密材料不应', prompt)
        self.assertNotIn('不应发送的私人核查备注', prompt)
        with self.assertRaises(WorkflowError):
            assessment_prompt(b, r, ['M2'])

    def assessment(self, b):
        return validate_assessment(dict(summary='需继续补采', fact_suggestions=[dict(fact_id='F1', suggested_claim='运营方表示尚未确定调整票价。', reason='采访补充', evidence=[dict(source_id='M1', quote=QUOTE, relation='支持')])], pitch_suggestions=[dict(pitch_id='P1', judgment='继续补采', reason='应获得正式决定', fact_ids=['F1'])]), b, ['M1'])

    def test_suggestions_are_opt_in_adopted_and_expire_on_revision(self):
        b, r = project()
        material(b, r, ai_allowed=True)
        result = self.assessment(b)
        old = b['brief'].facts[0].claim
        store_assessment(b, result, ['M1'])
        self.assertEqual(b['brief'].facts[0].claim, old)
        adopt_assessment(b, r, [0], [0], False)
        self.assertEqual(b['brief'].facts[0].claim, result.fact_suggestions[0].suggested_claim)
        self.assertEqual(fact_status(b['brief'].facts[0], r), '待复核')
        self.assertEqual(b['workflow'].decisions['P1'].status, '继续补采')
        with self.assertRaises(WorkflowError):
            adopt_assessment(b, r, [0], [], False)

    def test_bad_ai_quote_is_rejected(self):
        b, r = project()
        material(b, r, ai_allowed=True)
        payload = self.assessment(b).model_dump()
        payload['fact_suggestions'][0]['evidence'][0]['quote'] = '模型虚构并不存在的完整引语。'
        with self.assertRaises(WorkflowError):
            validate_assessment(payload, b, ['M1'])

    def test_invalid_adoption_is_transactional(self):
        b, r = project()
        material(b, r, ai_allowed=True)
        result = self.assessment(b)
        fact = b['brief'].facts[0]
        fact.evidence = [fact.evidence[0].model_copy(deep=True) for _ in range(6)]
        store_assessment(b, result, ['M1'])
        before = project_bytes(b, r)
        with self.assertRaises(WorkflowError):
            adopt_assessment(b, r, [0], [], False)
        self.assertEqual(project_bytes(b, r), before)

    def test_old_source_objects_are_migrated(self):
        b, r = project()
        source = b['sources'][0]
        del source.__dict__['origin']
        ensure_workflow(b)
        self.assertEqual(b['sources'][0].origin, 'web')

    def test_inference_and_missing_basis_cannot_be_verified(self):
        b, r = project()
        with self.assertRaises(WorkflowError):
            save_review(b, r, 'F1', '已核实', '')
        b['brief'].facts[0].kind = '分析推断'
        with self.assertRaises(WorkflowError):
            save_review(b, r, 'F1', '已核实', '仅属推断')


class WorkflowInteractionTests(unittest.TestCase):
    def demo(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        app.radio(key='mode').set_value('体验虚构样例').run()
        app.button(key='generate_brief').click().run()
        self.assertFalse(app.exception)
        return app

    def test_paste_update_save_and_restore(self):
        app = self.demo()
        app.text_input(key='material_title').set_value('虚构补充采访')
        app.text_area(key='material_text').set_value(QUOTE)
        app.text_area(key='material_quote').set_value(QUOTE)
        app.multiselect(key='material_facts').set_value(['F1'])
        app.selectbox(key='material_relation').set_value('反驳')
        app.button(key='save_material').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['brief_bundle']['sources']), 4)
        self.assertEqual(app.session_state['reviews']['F1']['status'], '待复核')
        self.assertTrue(app.button(key='reassess_project').disabled)
        raw = project_bytes(app.session_state['brief_bundle'], app.session_state['reviews'])
        restored, reviews = restore_project(raw)
        self.assertEqual(restored['sources'][-1].text, QUOTE)
        next(b for b in app.button if b.label.startswith('准备下载')).click().run()
        self.assertIn('采编推进', app.session_state['prepared_export']['markdown'])
        old_snapshot = app.session_state['prepared_export']['project_snapshot']
        app.text_area[0].set_value('新增核查备注').run()
        self.assertNotEqual(project_bytes(app.session_state['brief_bundle'], app.session_state['reviews']), old_snapshot)
        app.run()
        app.button(key='generate_brief').click().run()
        self.assertEqual(len(app.session_state['brief_bundle']['sources']), 4)
        self.assertIn('允许替换', app.error[0].value)

    def test_mock_reassessment_requires_consent_and_editor_adoption(self):
        app = self.demo()
        b = app.session_state['brief_bundle']
        material(b, app.session_state['reviews'], ai_allowed=True)
        app.run()
        selector = next(w for w in app.multiselect if w.label == '本轮允许发送的材料')
        selector.set_value(['M1']).run()
        self.assertTrue(app.button(key='reassess_project').disabled)
        consent = next(w for w in app.checkbox if w.label.startswith('同意将'))
        consent.check().run()
        app.text_input(key='deepseek_key').set_value('test-placeholder').run()
        payload = ReportingTests().assessment(app.session_state['brief_bundle']).model_dump_json()
        response = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=payload))])
        with patch('workflow_ui.OpenAI') as model:
            model.return_value.__enter__.return_value.chat.completions.create.return_value = response
            app.button(key='reassess_project').click().run()
        self.assertFalse(app.exception)
        self.assertIsNotNone(app.session_state['brief_bundle']['workflow'].assessment)
        self.assertNotEqual(app.session_state['brief_bundle']['brief'].facts[0].claim, '运营方表示尚未确定调整票价。')
        next(w for w in app.multiselect if w.label == '采纳哪些事实修订').set_value([0])
        app.button(key='adopt_assessment').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['brief_bundle']['brief'].facts[0].claim, '运营方表示尚未确定调整票价。')


if __name__ == '__main__':
    unittest.main()
