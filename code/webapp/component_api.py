"""Allowlisted API bridge for the original HTML interface on Streamlit."""
import json
from urllib.parse import parse_qs, urlsplit
from analysis import INPUT, OUTPUT


class RequestError(ValueError):
    pass


def bootstrap(configured):
    return {
        '/api/analysis': json.loads((OUTPUT / 'analysis.json').read_text(encoding='utf8')),
        '/api/manifest': json.loads((INPUT / 'manifest.json').read_text(encoding='utf8')),
        '/api/agent/status': {'configured': bool(configured)},
        '/api/status': {'running': False, 'message': '基线已完成', 'error': None},
    }


def route_request(request, matrix_for, get_agent):
    if not isinstance(request, dict):
        raise RequestError('请求格式无效。')
    if len(json.dumps(request, ensure_ascii=False).encode('utf8')) > 262144:
        raise RequestError('本次对话过长，请开始新对话后重试。')
    if not isinstance(request.get('url', ''), str) or not isinstance(request.get('method', 'GET'), str):
        raise RequestError('请求地址或方法格式无效。')
    url = urlsplit(request.get('url', ''))
    if url.scheme or url.netloc:
        raise RequestError('Only local analysis routes are supported')
    params = parse_qs(url.query)
    method = request.get('method', 'GET').upper()
    if method == 'POST':
        if url.path != '/api/agent/chat':
            raise RequestError('线上版本提供分析结果查询')
        try:
            body = json.loads(request.get('body') or '{}')
        except (ValueError, TypeError):
            raise RequestError('请求内容格式无效，请刷新页面后重试。') from None
        if not isinstance(body, dict):
            raise RequestError('请求内容须为对象。')
        return {'data': get_agent().chat(body.get('message', ''), body.get('history', []), context=body.get('context'), language=body.get('language', 'zh'))}
    if method != 'GET':
        raise RequestError('Unsupported request method')
    dataset = params.get('dataset', [''])[0]
    if url.path in ['/api/genes', '/api/expression', '/api/export']:
        try:
            matrix, genes = matrix_for(dataset)
        except KeyError:
            raise RequestError('数据集不存在，请重新选择。') from None
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
    raise RequestError('Unknown analysis route')
