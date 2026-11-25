"""Bundle the real demo and read-only API into one Cloudflare Worker."""
import base64
import gzip
import json
from pathlib import Path
import struct
import sys
import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/webapp'))
from deepseek_agent import Agent, SYSTEM, TOOLS
from example_io import load_counts


def packed(value):
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    return base64.b64encode(gzip.compress(data, mtime=0)).decode()


def build():
    inputs, output = ROOT / 'data/local_example', ROOT / 'runs/web_demo'
    analysis = json.loads((output / 'analysis.json').read_text(encoding='utf8'))
    manifest = json.loads((inputs / 'manifest.json').read_text(encoding='utf8'))
    assets, matrices, genes = {}, {}, {}
    for name, mime in [('index.html', 'text/html'), ('app.js', 'text/javascript'), ('style.css', 'text/css')]:
        text = (ROOT / 'code/webapp/static' / name).read_text(encoding='utf8')
        if name == 'index.html':
            text = text.replace('本地运行', '在线研究工作台').replace('本地示例项目', '示例项目').replace('本机真实数据', '真实示例数据')
            text = text.replace('所有图表来自本机真实数据，结果保存在项目 runs 目录。', '所有图表来自公开数据的实际计算结果。')
            text = text.replace('<button class="button primary" id="rebuild">重新运行示例基线</button>', '<button class="button secondary" id="rebuild" disabled title="下载仓库后使用 Python 重新计算">Python 建模 · 仓库可运行</button>')
        assets['/' if name == 'index.html' else '/' + name] = {'body': packed(text.encode()), 'mime': mime + '; charset=utf-8'}
    assets['/api/analysis'] = {'body': packed(analysis), 'mime': 'application/json; charset=utf-8'}
    assets['/api/manifest'] = {'body': packed(manifest), 'mime': 'application/json; charset=utf-8'}
    for item in manifest['datasets']:
        dataset_id = item['dataset_id']
        matrix = load_counts(inputs / item['counts']).tocsc()
        matrix.sort_indices()
        if matrix.shape[0] >= 65536 or matrix.max() >= 65536:
            raise ValueError('Demo binary format requires uint16 rows and counts')
        raw = struct.pack('<III', matrix.shape[0], matrix.shape[1], matrix.nnz)
        raw += matrix.indptr.astype('<u4').tobytes()
        raw += matrix.indices.astype('<u2').tobytes()
        raw += matrix.data.astype('<u2').tobytes()
        matrices[dataset_id] = packed(raw)
        genes[dataset_id] = pd.read_csv(inputs / item['genes'], sep='\t')['gene'].tolist()
        assets['/exports/' + dataset_id] = {'body': packed((output / f'{dataset_id}_annotations.tsv').read_bytes()), 'mime': 'text/tab-separated-values; charset=utf-8'}
    agent = Agent(output, lambda _: None)
    niches = {}
    for dataset in analysis['datasets']:
        if dataset['modality'] == 'spatial':
            for neighbors in [12, 24]:
                for clusters in [3, 4, 5, 6]:
                    args = {'dataset_id': dataset['id'], 'neighbors': neighbors, 'clusters': clusters}
                    niches[f'{dataset["id"]}:{neighbors}:{clusters}'] = agent.tool('get_niche_summary', args)
    payload = {'assets': assets, 'matrices': matrices, 'genes': genes, 'niches': niches, 'tools': TOOLS, 'prompt': SYSTEM}
    directory = ROOT / 'dist/server'
    directory.mkdir(parents=True, exist_ok=True)
    runtime = (ROOT / 'worker/runtime.mjs').read_text(encoding='utf8')
    entry = 'const BUNDLE=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n' + runtime
    (directory / 'index.js').write_text(entry, encoding='utf8')
    print(f'Built Worker: {len(entry.encode()) / 1024 / 1024:.2f} MiB, {len(matrices)} real datasets')


if __name__ == '__main__':
    build()
