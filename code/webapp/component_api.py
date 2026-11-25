"""Allowlisted API bridge for the original HTML interface on Streamlit."""
import json
from urllib.parse import parse_qs, urlsplit
from analysis import INPUT, OUTPUT


def bootstrap(configured):
    return {
        '/api/analysis': json.loads((OUTPUT / 'analysis.json').read_text(encoding='utf8')),
        '/api/manifest': json.loads((INPUT / 'manifest.json').read_text(encoding='utf8')),
        '/api/agent/status': {'configured': bool(configured)},
        '/api/status': {'running': False, 'message': '基线已完成', 'error': None},
    }


def route_request(request, matrix_for, get_agent):
    if not isinstance(request, dict) or len(json.dumps(request)) > 65536:
        raise ValueError('请求格式无效或过长')
    url = urlsplit(request.get('url', ''))
    if url.scheme or url.netloc:
        raise ValueError('Only local analysis routes are supported')
    params = parse_qs(url.query)
    method = request.get('method', 'GET').upper()
    if method == 'POST':
        if url.path != '/api/agent/chat':
            raise ValueError('线上版本提供分析结果查询')
        body = json.loads(request.get('body') or '{}')
        return {'data': get_agent().chat(body.get('message', ''), body.get('history', []), context=body.get('context'), language=body.get('language', 'zh'))}
    if method != 'GET':
        raise ValueError('Unsupported request method')
    dataset = params.get('dataset', [''])[0]
    if url.path in ['/api/genes', '/api/expression', '/api/export']:
        matrix, genes = matrix_for(dataset)
        if url.path == '/api/genes':
            term = params.get('q', [''])[0].upper()
            return {'data': [gene for gene in genes if term in gene.upper()][:60]}
        if url.path == '/api/export':
            return {'data': (OUTPUT / f'{dataset}_annotations.tsv').read_text(encoding='utf8'), 'content_type': 'text/tab-separated-values; charset=utf-8'}
        gene = params.get('gene', [''])[0]
        if gene not in genes:
            return {'data': {'gene': gene, 'measured': False}}
        values = matrix[:, genes.index(gene)].toarray().ravel()
        return {'data': {'gene': gene, 'measured': True, 'values': values.tolist(), 'positive': int((values > 0).sum()), 'cells': len(values)}}
    raise ValueError('Unknown analysis route')
