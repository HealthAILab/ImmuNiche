import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {expression, localTool} from '../dist/server/index.js';
import {execFileSync} from 'node:child_process';

test('binary expression API matches Python input matrix exactly', async () => {
  const script = `import json;from pathlib import Path;import pandas as pd;from scipy import sparse
p=Path('data/local_example');m=json.loads((p/'manifest.json').read_text(encoding='utf8'));out=[]
for d in m['datasets']:
 a=sparse.load_npz(p/d['counts']);g=pd.read_csv(p/d['genes'],sep='\\t')['gene'].tolist()
 for gene in ['MPST','PYCR1','CD68',g[-1]]:
  out.append({'dataset':d['dataset_id'],'gene':gene,'values':a[:,g.index(gene)].toarray().ravel().tolist() if gene in g else None})
print(json.dumps(out))`;
  const expected = JSON.parse(execFileSync('python',['-X','utf8','-c',script],{encoding:'utf8',maxBuffer:4*1024*1024}));
  for (const item of expected) {
    const result = await expression(item.dataset,item.gene);
    assert.equal(result.measured,item.values !== null);
    if (result.measured) assert.deepEqual(result.values,item.values);
  }
});

test('all spatial models retain center and neighbor counts', async () => {
  const data = await localTool('get_overview',{});
  for (const d of data.datasets.filter(d=>d.modality==='spatial')) for (const neighbors of [12,24]) for (const clusters of [3,4,5,6]) {
    const result = await localTool('get_niche_summary',{dataset_id:d.id,neighbors,clusters});
    assert.equal(result.niches.reduce((s,n)=>s+n.cells,0),d.cells);
    for (const n of result.niches) assert.equal(Object.values(n.neighbor_cell_type_occurrences).reduce((a,b)=>a+b,0),n.cells*neighbors);
  }
});

test('hosted UI omits credentials and provider name; requests obey origin boundary', async () => {
  const response = await worker.fetch(new Request('https://example.test/'),{});
  assert.equal(response.status,200);
  const html = await response.text();
  assert.doesNotMatch(html,/DeepSeek|API Key|agentKey/);
  const status = await worker.fetch(new Request('https://example.test/api/agent/status'),{DEEPSEEK_API_KEY:'test-only-secret'});
  assert.deepEqual(await status.json(),{configured:true});
  const cross = await worker.fetch(new Request('https://example.test/api/agent/chat',{method:'POST',headers:{Origin:'https://elsewhere.test','X-Requested-With':'NicheLab'},body:'{}'}),{});
  assert.equal(cross.status,403);
  const rebuild = await worker.fetch(new Request('https://example.test/api/rebuild',{method:'POST'}),{});
  assert.equal(rebuild.status,405);
});
