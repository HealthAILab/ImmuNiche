"""DeepSeek chat with bounded, read-only local analysis tools."""
from collections import Counter
import json
import os
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from scipy.spatial import cKDTree

BASE = 'https://api.deepseek.com'
SYSTEM = '''你是 ImmuNiche 科研助手，用中文简洁回答。先查询本地工具再引用数据数字。
主要工作是解读模型结果。解释每类生态位的细胞组成、样本间变化、归属及验证表现，
结合查询到的程序评分和基因覆盖解释生物学含义。用具体结果回答，并列出值得继续检验的线索。
使用短段落或简短列表，不使用表格。无需介绍模型厂商或接口配置。
中心细胞组成与邻域细胞组成分别解读；细胞组成不能直接证明组织边界、浸润、因果或功能。
生态位生物学名称作为候选命名，依照查询到的组成与表达结果说明依据。
这是肠癌开发子集：单细胞与空间来自不同队列。空间细胞类型为映射结果，Myeloids表示髓系。
当前生态位是邻域特征GMM基线，GNN尚未训练。表达评分不能当作代谢物、通量或修饰实测。
明确区分已查询的结果与后续建议。缺测基因不能描述为零表达。只操作提供的只读工具。'''


class AgentError(Exception):
    pass


def request_api(key, path, payload=None):
    request = Request(BASE + path, data=None if payload is None else json.dumps(payload).encode(),
                      headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as error:
        messages = {401: '分析服务认证失败，请检查服务端配置。', 402: '分析服务账户余额不足。',
                    429: '请求频率受限，请稍后重试。'}
        raise AgentError(messages.get(error.code, f'分析服务请求失败（HTTP {error.code}）。')) from None
    except (URLError, TimeoutError):
        raise AgentError('分析服务连接超时或网络不可用，请重试。') from None


def definition(name, description, properties=None, required=None):
    return {'type': 'function', 'function': {'name': name, 'description': description,
            'parameters': {'type': 'object', 'properties': properties or {},
                           'required': required or [], 'additionalProperties': False}}}


DATASET = {'dataset_id': {'type': 'string', 'description': 'get_overview 返回的数据集ID'}}
TOOLS = [definition('get_overview', '查询全部数据集、细胞组成、验证和方法'),
         definition('get_gene_stats', '查询基因实际覆盖、阳性数和计数统计',
                    {**DATASET, 'gene': {'type': 'string'}}, ['dataset_id', 'gene']),
         definition('get_program_summary', '查询程序基因覆盖及细胞类型表达评分', DATASET, ['dataset_id']),
         definition('get_niche_summary', '查询GMM生态位大小及中心细胞类型组成',
                    {**DATASET, 'neighbors': {'type': 'integer', 'enum': [12, 24]},
                     'clusters': {'type': 'integer', 'enum': [3, 4, 5, 6]}}, ['dataset_id', 'neighbors', 'clusters'])]


class Agent:
    def __init__(self, output, matrix_for, transport=request_api):
        self.output, self.matrix_for, self.transport = output, matrix_for, transport
        self.lock = threading.Lock()
        self.key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.models = []
        self.model = ''

    def status(self):
        with self.lock:
            return {'configured': bool(self.key and self.model), 'models': list(self.models), 'model': self.model}

    def configure(self, key, model=''):
        key = key.strip()
        if not key or len(key) > 512 or any(c.isspace() for c in key):
            raise AgentError('请填写有效的 DeepSeek API Key。')
        result = self.transport(key, '/models')
        models = [v['id'] for v in result.get('data', []) if isinstance(v.get('id'), str)]
        if not models:
            raise AgentError('账户未返回可用模型。')
        chosen = model if model in models else ('deepseek-flash' if 'deepseek-flash' in models else models[0])
        with self.lock:
            self.key, self.models, self.model = key, models, chosen
        return self.status()

    def clear(self):
        with self.lock:
            self.key, self.models, self.model = '', [], ''
        return self.status()

    def tool(self, name, args):
        data = json.loads((self.output / 'analysis.json').read_text(encoding='utf8'))
        if name == 'get_overview':
            return {**{k: data[k] for k in ['shared_genes', 'validation', 'gnn_status', 'methods']},
                    'datasets': [{k: d[k] for k in ['id', 'modality', 'cells', 'genes', 'type_counts']} for d in data['datasets']]}
        dataset = next((d for d in data['datasets'] if d['id'] == args.get('dataset_id')), None)
        if dataset is None:
            raise AgentError('数据集ID不存在，请先查询概览。')
        if name == 'get_gene_stats':
            gene = args.get('gene', '')
            if not isinstance(gene, str) or len(gene) > 80:
                raise AgentError('基因名称无效。')
            matrix, genes = self.matrix_for(dataset['id'])
            if gene not in genes:
                return {'dataset_id': dataset['id'], 'gene': gene, 'measured': False}
            vector = matrix[:, genes.index(gene)].toarray().ravel()
            return {'dataset_id': dataset['id'], 'gene': gene, 'measured': True,
                    'cells': len(vector), 'positive': int((vector > 0).sum()),
                    'positive_fraction': float((vector > 0).mean()), 'mean_raw_count': float(vector.mean())}
        if name == 'get_program_summary':
            return {k: dataset[k] for k in ['id', 'coverage', 'score_summary']}
        if name == 'get_niche_summary':
            neighbors, clusters = args.get('neighbors'), args.get('clusters')
            if neighbors not in [12, 24] or clusters not in [3, 4, 5, 6]:
                raise AgentError('请选择12或24近邻、3至6个生态位。')
            model = dataset.get('niche_models', {}).get(f'{neighbors}_{clusters}')
            if model is None:
                raise AgentError('该数据集没有空间生态位结果。')
            neighbor_indices = cKDTree(dataset['coords']).query(dataset['coords'], k=neighbors + 1)[1][:, 1:]
            return {'dataset_id': dataset['id'], 'method': 'GMM baseline', 'converged': model['converged'],
                    'neighbors': neighbors, 'clusters': clusters,
                    'niches': [{'niche': n + 1, 'cells': model['labels'].count(n),
                                'center_cell_types': dict(Counter(t for t, label in zip(dataset['labels'], model['labels']) if label == n)),
                                'neighbor_cell_type_occurrences': dict(Counter(dataset['labels'][j] for i, label in enumerate(model['labels']) if label == n for j in neighbor_indices[i])),
                                'neighbor_count_note': '邻居出现次数，重复邻居按各中心分别计数'}
                               for n in range(clusters)]}
        raise AgentError('工具不存在。')

    def chat(self, message, history=None, model='', context=None):
        if not isinstance(message, str) or not message.strip() or len(message) > 6000:
            raise AgentError('请输入6000字以内的问题。')
        with self.lock:
            key, chosen = self.key, model or self.model
            if not key or chosen not in self.models:
                raise AgentError('分析服务尚未启用，请完成服务端配置。')
        messages = [{'role': 'system', 'content': SYSTEM}]
        if isinstance(context, dict):
            overview = self.tool('get_overview', {})
            ids = [d['id'] for d in overview['datasets']]
            if context.get('dataset_id') in ids and context.get('neighbors') in [12, 24] and context.get('clusters') in [3, 4, 5, 6]:
                messages.append({'role': 'system', 'content': '网页当前选择的空间模型：' + json.dumps({k: context[k] for k in ['dataset_id', 'neighbors', 'clusters']}, ensure_ascii=False) + '。用户未指定参数时优先解读此模型。'})
        if not isinstance(history, list):
            raise AgentError('会话格式无效。')
        for item in history[-8:]:
            if isinstance(item, dict) and item.get('role') in ['user', 'assistant'] and isinstance(item.get('content'), str):
                messages.append({'role': item['role'], 'content': item['content'][:6000]})
        messages.append({'role': 'user', 'content': message})
        trace = []
        for step in range(6):
            result = self.transport(key, '/chat/completions', {'model': chosen, 'messages': messages,
                    'tools': TOOLS, 'max_tokens': 1800, 'thinking': {'type': 'disabled'}, 'stream': False})
            answer = result['choices'][0]['message']
            calls = answer.get('tool_calls') or []
            if not calls:
                return {'answer': answer.get('content') or '本次未返回文本，请重试。', 'trace': trace, 'model': chosen}
            if len(calls) > 8:
                raise AgentError('单轮查询工具过多，请缩小问题范围。')
            messages.append({k: answer[k] for k in ['role', 'content', 'tool_calls'] if k in answer})
            for call in calls:
                function = call['function']
                try:
                    args = json.loads(function['arguments'])
                    if not isinstance(args, dict):
                        raise AgentError('工具参数须为对象。')
                    value = self.tool(function['name'], args)
                except (AgentError, ValueError) as error:
                    args, value = {}, {'error': str(error)}
                trace.append({'tool': function['name'], 'arguments': args, 'result': value})
                messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(value, ensure_ascii=False)})
        raise AgentError('已达到本次查询轮数，请缩小问题范围后重试。')
