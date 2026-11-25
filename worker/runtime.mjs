const encoder = new TextEncoder();
const decoder = new TextDecoder();
async function unpack(encoded) {
  const binary = atob(encoded), bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
}
let analysisPromise;
const analysis = () => analysisPromise ||= unpack(BUNDLE.assets['/api/analysis'].body).then(bytes => JSON.parse(decoder.decode(bytes)));
function json(value, status = 200) { return new Response(JSON.stringify(value), {status, headers: {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}}); }
async function expression(dataset, gene) {
  const genes = BUNDLE.genes[dataset];
  if (!genes) throw new Error('数据集不存在');
  const column = genes.indexOf(gene);
  if (column < 0) return {gene, measured: false};
  const buffer = await unpack(BUNDLE.matrices[dataset]), view = new DataView(buffer);
  const rows = view.getUint32(0, true), cols = view.getUint32(4, true), nnz = view.getUint32(8, true);
  const indicesStart = 12 + (cols + 1) * 4, valuesStart = indicesStart + nnz * 2;
  const start = view.getUint32(12 + column * 4, true), end = view.getUint32(12 + (column + 1) * 4, true);
  const values = new Array(rows).fill(0);
  for (let i = start; i < end; i++) values[view.getUint16(indicesStart + i * 2, true)] = view.getUint16(valuesStart + i * 2, true);
  return {gene, measured: true, values, positive: values.filter(v => v > 0).length, cells: rows};
}
async function localTool(name, args) {
  const data = await analysis();
  if (name === 'get_overview') return {shared_genes: data.shared_genes, validation: data.validation, gnn_status: data.gnn_status, methods: data.methods, datasets: data.datasets.map(d => ({id: d.id, modality: d.modality, cells: d.cells, genes: d.genes, type_counts: d.type_counts}))};
  const dataset = data.datasets.find(d => d.id === args.dataset_id);
  if (!dataset) throw new Error('请先查询数据集ID');
  if (name === 'get_gene_stats') {
    if (typeof args.gene !== 'string' || args.gene.length > 80) throw new Error('基因名称无效');
    const result = await expression(dataset.id, args.gene);
    if (!result.measured) return {dataset_id: dataset.id, gene: args.gene, measured: false};
    return {dataset_id: dataset.id, gene: args.gene, measured: true, cells: result.cells, positive: result.positive, positive_fraction: result.positive / result.cells, mean_raw_count: result.values.reduce((a,b) => a+b,0) / result.cells};
  }
  if (name === 'get_program_summary') return {id: dataset.id, coverage: dataset.coverage, score_summary: dataset.score_summary};
  if (name === 'get_niche_summary') {
    const result = BUNDLE.niches[`${dataset.id}:${args.neighbors}:${args.clusters}`];
    if (!result) throw new Error('该模型不存在');
    return result;
  }
  throw new Error('工具不存在');
}
async function provider(env, messages) {
  const response = await fetch('https://api.deepseek.com/chat/completions', {method: 'POST', headers: {'Authorization': `Bearer ${env.DEEPSEEK_API_KEY}`, 'Content-Type': 'application/json'}, body: JSON.stringify({model: env.DEEPSEEK_MODEL || 'deepseek-flash', messages, tools: BUNDLE.tools, thinking: {type: 'disabled'}, max_tokens: 1800, stream: false}), signal: AbortSignal.timeout(60000)});
  if (!response.ok) throw new Error(`分析服务请求失败（${response.status}）`);
  const result = await response.json();
  return result.choices[0].message;
}
async function chat(env, body) {
  if (!env.DEEPSEEK_API_KEY) throw new Error('分析服务尚未配置');
  if (typeof body.message !== 'string' || !body.message.trim() || body.message.length > 6000) throw new Error('请输入6000字以内的问题');
  const messages = [{role: 'system', content: BUNDLE.prompt}];
  const context = body.context;
  if (context && BUNDLE.niches[`${context.dataset_id}:${context.neighbors}:${context.clusters}`]) messages.push({role: 'system', content: '优先解读当前空间模型：' + JSON.stringify({dataset_id: context.dataset_id, neighbors: context.neighbors, clusters: context.clusters})});
  for (const item of (Array.isArray(body.history) ? body.history : []).slice(-8)) if (['user','assistant'].includes(item?.role) && typeof item.content === 'string') messages.push({role: item.role, content: item.content.slice(0,6000)});
  messages.push({role: 'user', content: body.message});
  const trace = [];
  for (let round = 0; round < 6; round++) {
    const answer = await provider(env, messages), calls = answer.tool_calls || [];
    if (!calls.length) return {answer: answer.content || '请重试', trace};
    if (calls.length > 8) throw new Error('查询过多，请缩小范围');
    messages.push({role: 'assistant', content: answer.content, tool_calls: calls});
    for (const call of calls) {
      let args = {}, result;
      try { args = JSON.parse(call.function.arguments); if (!args || Array.isArray(args) || typeof args !== 'object') throw new Error('参数无效'); result = await localTool(call.function.name, args); }
      catch (error) { result = {error: error.message}; }
      trace.push({tool: call.function.name, arguments: args, result});
      messages.push({role: 'tool', tool_call_id: call.id, content: JSON.stringify(result)});
    }
  }
  throw new Error('本次查询轮数已用完，请缩小问题范围');
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url), path = url.pathname;
    try {
      if (request.method === 'POST') {
        if (path !== '/api/agent/chat') return json({error: '线上版提供结果查询，建模请运行仓库内的 Python 程序'},405);
        if (request.headers.get('X-Requested-With') !== 'NicheLab' || (request.headers.get('Origin') && request.headers.get('Origin') !== url.origin)) return json({error:'请求来源无效'},403);
        const text = await request.text();
        if (encoder.encode(text).length > 65536) return json({error:'请求过长'},413);
        return json(await chat(env, JSON.parse(text)));
      }
      if (request.method !== 'GET' && request.method !== 'HEAD') return json({error:'Method not allowed'},405);
      if (path === '/api/agent/status') return json({configured: Boolean(env.DEEPSEEK_API_KEY)});
      if (path === '/api/status') return json({running:false,message:'在线结果已就绪',error:null});
      if (path === '/api/expression') return json(await expression(url.searchParams.get('dataset'), url.searchParams.get('gene')));
      if (path === '/api/genes') {
        const genes = BUNDLE.genes[url.searchParams.get('dataset')];
        if (!genes) return json({error:'Unknown dataset'},404);
        const term = (url.searchParams.get('q') || '').toUpperCase();
        return json(genes.filter(g => g.toUpperCase().includes(term)).slice(0,60));
      }
      const route = path === '/api/export' ? '/exports/' + url.searchParams.get('dataset') : path;
      const asset = BUNDLE.assets[route];
      if (!asset) return json({error:'Not found'},404);
      const headers = {'Content-Type':asset.mime,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin'};
      if (path === '/api/export') headers['Content-Disposition'] = 'attachment; filename="annotations.tsv"';
      return new Response(request.method === 'HEAD' ? null : await unpack(asset.body),{headers});
    } catch (error) {
      return json({error: error.name === 'TimeoutError' ? '分析服务超时，请重试' : (error.message || '请求失败')});
    }
  }
};
export {expression, localTool};
