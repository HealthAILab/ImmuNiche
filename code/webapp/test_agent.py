"""Focused offline tests; never contacts DeepSeek."""
import json
import unittest
from analysis import OUTPUT
from deepseek_agent import Agent, AgentError
from server import matrix_for


class AgentTests(unittest.TestCase):
    def test_placeholder_key_rejected_before_network(self):
        calls = []
        agent = Agent(OUTPUT, matrix_for, lambda *args: calls.append(args))
        with self.assertRaises(AgentError):
            agent.configure('你之前提供的Key')
        self.assertEqual(calls, [])

    def test_real_tools(self):
        agent = Agent(OUTPUT, matrix_for)
        overview = agent.tool('get_overview', {})
        self.assertEqual(len(overview['datasets']), 3)
        for dataset in overview['datasets']:
            result = agent.tool('get_gene_stats', {'dataset_id': dataset['id'], 'gene': 'MPST'})
            self.assertEqual(result['measured'], dataset['modality'] == 'scrna')
            if dataset['modality'] == 'spatial':
                niches = agent.tool('get_niche_summary', {'dataset_id': dataset['id'], 'neighbors': 12, 'clusters': 4})
                self.assertEqual(sum(n['cells'] for n in niches['niches']), dataset['cells'])
                for niche in niches['niches']:
                    self.assertEqual(sum(niche['neighbor_cell_type_occurrences'].values()), niche['cells'] * 12)
        with self.assertRaises(AgentError):
            agent.tool('get_gene_stats', {'dataset_id': '../secret', 'gene': 'MPST'})

    def test_provider_tool_roundtrip_and_secret(self):
        calls = []

        def transport(key, path, payload=None):
            calls.append((path, payload))
            if path == '/models':
                return {'data': [{'id': 'test-model'}]}
            if len(calls) == 2:
                return {'choices': [{'message': {'role': 'assistant', 'content': None, 'tool_calls': [
                    {'id': 'call1', 'type': 'function', 'function': {'name': 'get_overview', 'arguments': '{}'}}]}}]}
            self.assertEqual(payload['messages'][-1]['role'], 'tool')
            return {'choices': [{'message': {'role': 'assistant', 'content': '已查询本地结果'}}]}

        agent = Agent(OUTPUT, matrix_for, transport)
        status = agent.configure('unit-test-key')
        self.assertNotIn('unit-test-key', json.dumps(status))
        result = agent.chat('概括结果', [])
        self.assertEqual(result['trace'][0]['tool'], 'get_overview')
        self.assertEqual(result['answer'], '已查询本地结果')
        self.assertNotIn('unit-test-key', json.dumps(result))
        self.assertFalse(agent.clear()['configured'])
        with self.assertRaises(AgentError):
            agent.chat('概括结果', [])


if __name__ == '__main__':
    unittest.main()
