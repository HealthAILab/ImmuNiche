"""ImmuNiche: public Streamlit research workspace."""
from collections import Counter
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import plotly.express as px
from scipy import sparse
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'code/webapp'))
from analysis import INPUT, OUTPUT, run
from example_io import load_counts
from deepseek_agent import Agent, AgentError

st.set_page_config(page_title='ImmuNiche', page_icon='◈', layout='wide')
st.markdown('''<style>
.stApp,[data-testid="stSidebar"]{background:#fff;color:#20334a}
[data-testid="stSidebar"]{border-right:1px solid #e5eaf0}
[data-testid="stMetric"]{border:1px solid #e5eaf0;border-radius:12px;padding:18px;background:#fff}
.block-container{padding-top:2rem;max-width:1500px}h1,h2,h3{color:#20334a}
[data-testid="stChatMessage"]{background:#f8fafc;border:1px solid #e5eaf0}
</style>''', unsafe_allow_html=True)


@st.cache_data(show_spinner='正在读取分析结果…')
def load_results():
    path = OUTPUT / 'analysis.json'
    if not path.exists():
        if not (INPUT / 'scrna_crc/counts.npz').exists() and not (INPUT / 'scrna_crc/counts.npz.part000').exists():
            raise FileNotFoundError('缺少示例输入，请先运行 code/prepare_local_example.py')
        run()
    return json.loads(path.read_text(encoding='utf8'))


@lru_cache(maxsize=3)
def matrix_for(dataset_id):
    manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf8'))
    item = next((d for d in manifest['datasets'] if d['dataset_id'] == dataset_id), None)
    if not item:
        raise KeyError('数据集不存在')
    return load_counts(INPUT / item['counts']), pd.read_csv(INPUT / item['genes'], sep='\t')['gene'].tolist()


def expression(dataset, gene):
    matrix, genes = matrix_for(dataset['id'])
    if gene not in genes:
        return None
    return matrix[:, genes.index(gene)].toarray().ravel()


def secret(name):
    try:
        return str(st.secrets.get(name, os.environ.get(name, '')))
    except (FileNotFoundError, KeyError):
        return os.environ.get(name, '')


@st.cache_resource(show_spinner=False)
def agent_for(_key):
    agent = Agent(OUTPUT, matrix_for)
    agent.configure(_key)
    return agent


def scatter(dataset, colors, color_label, continuous=False, key='plot'):
    xy = np.asarray(dataset['coords'])
    frame = pd.DataFrame({'x': xy[:, 0], 'y': xy[:, 1], color_label: colors,
                          '细胞ID': dataset['cell_ids'], '细胞类型': [names.get(t, t) for t in dataset['labels']]})
    chart = px.scatter(frame, x='x', y='y', color=color_label,
                       color_discrete_sequence=px.colors.qualitative.Safe,
                       color_continuous_scale='Blues', hover_data=['细胞ID', '细胞类型'], render_mode='webgl')
    chart.update_traces(marker={'size': 4, 'opacity': 0.85})
    chart.update_layout(height=560, paper_bgcolor='white', plot_bgcolor='white',
                        margin={'l': 0, 'r': 0, 'b': 0, 't': 10}, legend_title_text=color_label,
                        dragmode='pan', font={'color': '#334155'})
    if dataset['modality'] == 'spatial':
        chart.update_yaxes(scaleanchor='x', scaleratio=1)
    st.plotly_chart(chart, width="stretch", key=key, config={'displaylogo': False, 'scrollZoom': True, 'toImageButtonOptions': {'format': 'png', 'filename': key}})


def composition(counts, title):
    st.subheader(title)
    total = sum(counts.values())
    for label, count in sorted(counts.items(), key=lambda v: -v[1]):
        st.write(f'{names.get(label, label)}：{count:,}（{count / max(1,total):.1%}）')
        st.progress(count / max(1, total))


def export(dataset):
    path = OUTPUT / f'{dataset["id"]}_annotations.tsv'
    if path.exists():
        st.download_button('下载逐细胞结果', path.read_bytes(), file_name=path.name, mime='text/tab-separated-values', key='export-' + dataset['id'])


try:
    data = load_results()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()
names = data['type_names']
reference = next(d for d in data['datasets'] if d['modality'] == 'scrna')
spatial_items = [d for d in data['datasets'] if d['modality'] == 'spatial']
with st.sidebar:
    st.title('ImmuNiche')
    st.caption('免疫细胞状态与空间生态位')
    page = st.radio('分析工作台', ['数据概览', '细胞状态与代谢', '空间与生态位', '模型结果', '智能体'], label_visibility='collapsed')
    st.divider()
    sample_id = st.selectbox('空间样本', [d['id'] for d in spatial_items], format_func=lambda value: next(d['name'] for d in spatial_items if d['id'] == value))
    neighbors = st.selectbox('邻居数', [12, 24])
    clusters = st.selectbox('生态位数', [3, 4, 5, 6], index=1)
    st.caption('真实公开数据 · 开发示例')
spatial = next(d for d in spatial_items if d['id'] == sample_id)
context = {'dataset_id': sample_id, 'neighbors': neighbors, 'clusters': clusters}
model = spatial['niche_models'][f'{neighbors}_{clusters}']

if page == '数据概览':
    st.title('从细胞状态，看到组织环境')
    st.write('GSE132465 单细胞 × Vizgen 肠癌空间数据')
    metrics = st.columns(4)
    for column, (label, value) in zip(metrics, [('单细胞', reference['cells']), ('空间细胞', sum(d['cells'] for d in spatial_items)), ('共有基因', data['shared_genes']), ('空间样本', len(spatial_items))]):
        column.metric(label, f'{value:,}')
    for dataset in data['datasets']:
        with st.container(border=True):
            st.subheader(dataset['name'])
            st.write(f"{dataset['cells']:,} 个细胞 · {dataset['genes']:,} 个基因 · {dataset['source']}")
    st.subheader('分析流程')
    st.write('表达与细胞类型 → 共有基因映射 → 多尺度空间邻域 → 生态位基线 → 模型结果解读')
    st.caption('当前模型为 kNN 映射与 GMM 生态位基线；双分支 GNN 待接入。')
    st.download_button('下载输入清单', (INPUT / 'manifest.json').read_bytes(), 'manifest.json', 'application/json')

elif page == '细胞状态与代谢':
    st.title('细胞状态与代谢')
    choice = st.selectbox('着色方式', ['原作者细胞类型', '患者', '表达程序', '基因表达'])
    colors, label = [names.get(t, t) for t in reference['labels']], '细胞类型'
    if choice == '患者':
        colors, label = reference['patients'], '患者'
    elif choice == '表达程序':
        program = st.selectbox('表达程序', list(reference['program_scores']), format_func=lambda key: reference['coverage'][key]['name'])
        colors, label = reference['program_scores'][program], reference['coverage'][program]['name']
    elif choice == '基因表达':
        gene = st.text_input('表达基因', 'MPST').strip()
        values = expression(reference, gene)
        if values is None:
            st.info(f'{gene} 未列于当前基因清单')
            st.stop()
        colors, label = values, gene + ' 原始计数'
        st.caption(f'阳性细胞：{int((values > 0).sum()):,} / {len(values):,}')
    scatter(reference, colors, label, key='reference')
    composition(reference['type_counts'], '细胞组成')
    export(reference)

elif page == '空间与生态位':
    st.title('空间与生态位')
    st.caption(f"{spatial['name']} · {neighbors} 近邻 · {clusters} 个生态位 · {'已收敛' if model['converged'] else '未收敛'}")
    choice = st.selectbox('着色方式', ['生态位', '映射细胞类型', '映射支持度', '基因表达'])
    colors, label = [f'生态位 {n+1}' for n in model['labels']], '生态位'
    if choice == '映射细胞类型':
        colors, label = [names.get(t, t) for t in spatial['labels']], '细胞类型'
    elif choice == '映射支持度':
        colors, label = spatial['support'], '映射支持度'
    elif choice == '基因表达':
        gene = st.text_input('表达基因', 'CD68').strip()
        values = expression(spatial, gene)
        if values is None:
            st.info(f'{gene} 未列于这份空间面板')
            st.stop()
        colors, label = values, gene + ' 原始计数'
    scatter(spatial, colors, label, key=f'spatial-{sample_id}-{neighbors}-{clusters}')
    niche = st.selectbox('查看生态位组成', list(range(clusters)), format_func=lambda n: f'生态位 {n+1}')
    counts = Counter(t for t, n in zip(spatial['labels'], model['labels']) if n == niche)
    composition(counts, '中心细胞类型组成')
    with st.expander('空间表达程序覆盖'):
        for coverage in spatial['coverage'].values():
            st.write(f"{coverage['name']}：{len(coverage['present'])}/{coverage['total']} 个基因 · {'可显示' if coverage['available'] else '覆盖不足'}")
    export(spatial)

elif page == '模型结果':
    st.title('模型结果与验证')
    for item in data['validation']:
        with st.container(border=True):
            st.subheader('留出患者 ' + item['patient'])
            st.write(f"{item['cells']:,} 个细胞 · 准确率 {item['accuracy']:.1%} · Macro-F1 {item['macro_f1']:.3f}")
    for text in data['methods'].values():
        st.write(text)
    st.download_button('下载完整分析结果', json.dumps(data, ensure_ascii=False).encode(), 'analysis.json', 'application/json')

else:
    st.title('智能体')
    st.write('解读生态位特征、比较样本差异，结合基因表达解释模型结果。')
    st.caption(f"当前模型：{spatial['name']} · {neighbors} 近邻 · {clusters} 个生态位")
    key = secret('DEEPSEEK_API_KEY')
    if not key:
        st.info('分析服务待启用。')
    if st.button('新对话'):
        st.session_state['conversation'] = []
    conversation = st.session_state.setdefault('conversation', [])
    for message in conversation:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
            if message.get('trace'):
                with st.expander('查询依据'):
                    st.json(message['trace'])
    question = st.chat_input('输入要解读的问题…', disabled=not key, max_chars=6000)
    if question:
        with st.chat_message('user'):
            st.write(question)
        try:
            with st.spinner('正在查询和解读…'):
                result = agent_for(key).chat(question, [{'role': m['role'], 'content': m['content']} for m in conversation[-8:]], context=context)
            conversation.extend([{'role': 'user', 'content': question}, {'role': 'assistant', 'content': result['answer'], 'trace': result['trace']}])
            st.rerun()
        except AgentError as error:
            st.error(str(error))
