import unittest
import json
from types import SimpleNamespace
from component_api import bootstrap, route_request
from server import matrix_for


class ComponentTests(unittest.TestCase):
    def test_chinese_history_uses_actual_utf8_size(self):
        history = [{'role': 'assistant', 'content': '生态位' * 1500} for _ in range(3)]
        request = {'url': '/api/agent/chat', 'method': 'POST', 'body': json.dumps({'message': '解释模型', 'history': history}, ensure_ascii=False)}
        self.assertGreater(len(json.dumps(request)), 65536)
        self.assertLess(len(json.dumps(request, ensure_ascii=False).encode('utf8')), 65536)
        agent = SimpleNamespace(chat=lambda *args, **kwargs: {'answer': '已查询', 'trace': []})
        self.assertEqual(route_request(request, matrix_for, lambda: agent)['data']['answer'], '已查询')

    def test_real_expression_and_export(self):
        result = route_request({'url': '/api/expression?dataset=GSE132465_demo&gene=MPST'}, matrix_for, None)['data']
        self.assertTrue(result['measured'])
        self.assertEqual(len(result['values']), 2709)
        missing = route_request({'url': '/api/expression?dataset=HumanColonCancerPatient1_demo&gene=MPST'}, matrix_for, None)['data']
        self.assertFalse(missing['measured'])
        export = route_request({'url': '/api/export?dataset=GSE132465_demo'}, matrix_for, None)
        self.assertIn('cell_id', export['data'].splitlines()[0])

    def test_scope_and_agent(self):
        for request in [{'url': 'https://example.com'}, {'url': '/api/rebuild', 'method': 'POST'}, {'url': '/private/file'}]:
            with self.assertRaises(ValueError):
                route_request(request, matrix_for, None)
        captured = {}
        def chat(*args, **kwargs):
            captured.update(kwargs)
            return {'answer': 'Example', 'trace': []}
        response = route_request({'url': '/api/agent/chat', 'method': 'POST', 'body': '{"message":"Explain","language":"en"}'}, matrix_for, lambda: SimpleNamespace(chat=chat))
        self.assertEqual(captured['language'], 'en')
        self.assertEqual(response['data']['answer'], 'Example')
        self.assertEqual(bootstrap(True)['/api/agent/status'], {'configured': True})


if __name__ == '__main__':
    unittest.main()
