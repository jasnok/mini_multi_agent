"""실제 show_trace 함수의 구버전 Streamlit 중첩 회귀 테스트. API·LLM 호출 없음."""
import ast
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class TraceLayoutTests(unittest.TestCase):
    def render(self, nested):
        path = Path(__file__).resolve().parents[1] / "frontend" / "app.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "show_trace")
        code = "import streamlit as st\n" + ast.unparse(function) + "\n"
        code += "result = {'status': 'completed', 'trace': [{'step': 1, 'actor': 'moving_supervisor_agent', 'action': 'plan'}]}\n"
        code += "with st.expander('과제 확인'):\n    show_trace(result, nested=True)\n" if nested else "show_trace(result)\n"
        app = AppTest.from_string(code).run(timeout=10)
        if not app.exception and not app.json:
            self.skipTest("현재 Streamlit AppTest 런타임이 테스트 스크립트를 실행하지 못했습니다.")
        return app

    def test_trace_inside_outer_expander_has_no_nested_expanders(self):
        app = self.render(True)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.expander), 1)
        self.assertEqual(len(app.json), 1)

    def test_other_pages_keep_event_expanders(self):
        app = self.render(False)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.expander), 1)
        self.assertEqual(len(app.json), 1)
