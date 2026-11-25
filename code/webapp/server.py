"""Loopback-only local viewer. Run with Python; no web framework required."""
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import argparse
import json
import threading
import traceback
import numpy as np
import pandas as pd
from scipy import sparse
from analysis import INPUT, OUTPUT, run
from deepseek_agent import Agent, AgentError

STATIC = Path(__file__).resolve().parent / 'static'
job = {'running': False, 'message': '就绪', 'error': None}
lock = threading.Lock()

@lru_cache(maxsize=3)
def matrix_for(dataset_id):
    items = json.loads((INPUT / 'manifest.json').read_text(encoding='utf8'))['datasets']
    item = next((v for v in items if v['dataset_id'] == dataset_id), None)
    if item is None:
        raise KeyError('Unknown dataset')
    return sparse.load_npz(INPUT / item['counts']), pd.read_csv(INPUT / item['genes'], sep='\t')['gene'].tolist()

agent = Agent(OUTPUT, matrix_for)

def rebuild():
    try:
        run(lambda message: job.update(message=message))
        job.update(message='基线分析完成', error=None)
    except Exception:
        traceback.print_exc()
        job.update(message='计算失败，请查看终端日志', error='计算失败')
    finally:
        with lock:
            job['running'] = False

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def send_bytes(self, body, content_type, filename=None):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value):
        self.send_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), 'application/json; charset=utf-8')

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        try:
            if url.path == '/api/agent/status':
                return self.send_json(agent.status())
            if url.path == '/api/status':
                return self.send_json(job)
            if url.path == '/api/analysis':
                path = OUTPUT / 'analysis.json'
                if not path.exists():
                    return self.send_error(503, 'Analysis not ready')
                return self.send_bytes(path.read_bytes(), 'application/json; charset=utf-8')
            if url.path == '/api/manifest':
                return self.send_bytes((INPUT / 'manifest.json').read_bytes(), 'application/json; charset=utf-8', 'manifest.json')
            if url.path in ['/api/expression', '/api/genes']:
                matrix, genes = matrix_for(query.get('dataset', [''])[0])
                if url.path == '/api/genes':
                    term = query.get('q', [''])[0].upper()
                    return self.send_json([g for g in genes if term in g.upper()][:60])
                gene = query.get('gene', [''])[0]
                if gene not in genes:
                    return self.send_json({'gene': gene, 'measured': False})
                vector = matrix[:, genes.index(gene)].toarray().ravel()
                return self.send_json({'gene': gene, 'measured': True, 'values': vector.tolist(),
                                       'positive': int((vector > 0).sum()), 'cells': len(vector)})
            if url.path == '/api/export':
                dataset_id = query.get('dataset', [''])[0]
                matrix_for(dataset_id)
                path = OUTPUT / f'{dataset_id}_annotations.tsv'
                return self.send_bytes(path.read_bytes(), 'text/tab-separated-values; charset=utf-8', 'annotations.tsv')
        except KeyError:
            return self.send_error(404, 'Unknown dataset')
        except Exception:
            traceback.print_exc()
            return self.send_error(500, 'Unable to read analysis data')
        if url.path.startswith('/api/'):
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in ['/api/rebuild', '/api/agent/chat']:
            return self.send_error(404)
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{host}':
            return self.send_error(403)
        if self.headers.get('X-Requested-With') != 'NicheLab':
            return self.send_error(403)
        if route.startswith('/api/agent/'):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 65536:
                    raise AgentError('请求内容过长。')
                body = json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(body, dict):
                    raise AgentError('请求格式无效。')
                result = agent.chat(body.get('message', ''), body.get('history', []), context=body.get('context'))
                return self.send_json(result)
            except AgentError as error:
                return self.send_json({'error': str(error)})
            except (ValueError, TypeError, AttributeError):
                return self.send_json({'error': '请求或服务返回的格式无效。'})
            except Exception:
                # Do not log provider objects or requests containing credentials.
                return self.send_json({'error': '智能体请求失败，请重试。'})
        with lock:
            if job['running']:
                return self.send_json(job)
            job.update(running=True, message='开始读取示例数据', error=None)
            threading.Thread(target=rebuild, daemon=True).start()
        self.send_json(job)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if agent.key:
        try:
            agent.configure(agent.key)
        except AgentError as error:
            print(str(error), flush=True)
    if not (OUTPUT / 'analysis.json').exists():
        run(lambda message: print(message, flush=True))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Local: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
