"""Real-data demonstration baselines for the local immune-niche viewer."""
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import sparse
from example_io import load_counts
from scipy.spatial import cKDTree
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, accuracy_score

PROJECT = Path(__file__).resolve().parents[2]
INPUT = PROJECT / 'data/local_example'
OUTPUT = PROJECT / 'runs/web_demo'
PROGRAMS = {
    'proline': ('脯氨酸相关表达', ['PYCR1', 'PYCR2', 'PYCR3', 'ALDH18A1', 'PRODH', 'ALDH4A1', 'OAT']),
    'sulfur': ('活性硫／氧化还原相关表达', ['CBS', 'CTH', 'MPST', 'GOT1', 'GOT2', 'SLC7A11', 'GCLC', 'GCLM', 'GSS', 'SQOR', 'ETHE1', 'TST']),
    'presentation': ('抗原呈递', ['HLA-DRA', 'HLA-DPA1', 'HLA-DPB1', 'HLA-DQA1', 'CD74', 'B2M', 'TAP1']),
    'inflammation': ('炎症相关表达', ['IL1B', 'TNF', 'CXCL8', 'CCL2', 'NFKB1', 'NFKB2', 'TLR2']),
    'regulation': ('免疫调节相关表达', ['IL10', 'TGFB1', 'CD274', 'PDCD1LG2', 'IDO1', 'SOCS3']),
    'matrix': ('基质重塑相关表达', ['COL1A1', 'COL1A2', 'COL3A1', 'FAP', 'ACTA2', 'MMP2', 'MMP9']),
    'cytotoxic': ('细胞毒相关表达', ['CD8A', 'GZMA', 'GZMB', 'PRF1', 'NKG7', 'GNLY']),
}
ALIASES = {'PYCRL': 'PYCR3', 'SQRDL': 'SQOR'}
TYPE_NAMES = {
    'Epithelial cells': '上皮细胞', 'T cells': 'T细胞', 'Myeloids': '髓系细胞',
    'B cells': 'B细胞', 'Stromal cells': '基质细胞', 'Mast cells': '肥大细胞', 'Uncertain': '待确认',
}

def load_input(item):
    matrix = load_counts(INPUT / item['counts']).tocsr().astype(np.float32)
    genes = pd.read_csv(INPUT / item['genes'], sep='\t')['gene'].tolist()
    obs = pd.read_csv(INPUT / item['observations'], sep='\t', index_col=0)
    if matrix.shape != (len(obs), len(genes)) or not obs.index.is_unique:
        raise ValueError(f"Input alignment failed: {item['dataset_id']}")
    if not np.isfinite(matrix.data).all() or (matrix.data < 0).any():
        raise ValueError('Invalid expression counts')
    return matrix, genes, obs

def normalize(matrix):
    totals = np.asarray(matrix.sum(axis=1)).ravel()
    normalized = sparse.diags(10000 / np.maximum(totals, 1)) @ matrix
    normalized = normalized.tocsr()
    normalized.data = np.log1p(normalized.data)
    return normalized

def program_scores(matrix, genes):
    positions = {ALIASES.get(g, g): i for i, g in enumerate(genes)}
    expression = normalize(matrix)
    scores, coverage = {}, {}
    for key, (name, members) in PROGRAMS.items():
        present = [g for g in members if g in positions]
        available = len(present) >= 3 and len(present)/len(members) >= .5
        coverage[key] = {'name': name, 'present': present, 'total': len(members), 'available': available}
        if available:
            scores[key] = np.asarray(expression[:, [positions[g] for g in present]].mean(axis=1)).ravel()
    return scores, coverage

def round_list(array, decimals=4):
    return np.round(np.asarray(array), decimals).tolist()

def neighbors(xy, k):
    _, indices = cKDTree(xy).query(xy, k=min(k+1, len(xy)))
    return np.array([[j for j in row if j != i][:k] for i, row in enumerate(indices)])

def run(progress=print):
    manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf8'))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    progress('读取三份示例输入')
    loaded = {item['dataset_id']: (item, *load_input(item)) for item in manifest['datasets']}
    ref_id = next(k for k, v in loaded.items() if v[0]['modality'] == 'scrna')
    ref_item, ref_x, ref_genes, ref_obs = loaded[ref_id]
    common = sorted(set.intersection(*(set(v[2]) for v in loaded.values())))
    common_matrices = {}
    for key, (_, matrix, genes, _) in loaded.items():
        ix = pd.Index(genes).get_indexer(common)
        common_matrices[key] = normalize(matrix[:, ix]).toarray()
    labels = ref_obs['cell_type_reference'].astype(str).to_numpy()
    patients = ref_obs['patient_id'].astype(str).to_numpy()
    progress('按患者验证共有基因细胞类型映射')
    folds, prediction_rows = [], []
    for patient in sorted(set(patients)):
        test = patients == patient
        scaler = StandardScaler().fit(common_matrices[ref_id][~test])
        pca = PCA(n_components=20, random_state=42).fit(scaler.transform(common_matrices[ref_id][~test]))
        classifier = KNeighborsClassifier(n_neighbors=15, weights='distance')
        classifier.fit(pca.transform(scaler.transform(common_matrices[ref_id][~test])), labels[~test])
        predicted = classifier.predict(pca.transform(scaler.transform(common_matrices[ref_id][test])))
        folds.append({'patient': patient, 'cells': int(test.sum()), 'accuracy': float(accuracy_score(labels[test], predicted)),
                      'macro_f1': float(f1_score(labels[test], predicted, average='macro', zero_division=0))})
        prediction_rows.extend({'cell_id': str(cell), 'patient': patient, 'reference': truth, 'predicted': pred}
                               for cell, truth, pred in zip(ref_obs.index[test], labels[test], predicted))
    pd.DataFrame(prediction_rows).to_csv(OUTPUT / 'reference_validation.tsv', sep='\t', index=False)
    scaler = StandardScaler().fit(common_matrices[ref_id])
    pca = PCA(n_components=20, random_state=42).fit(scaler.transform(common_matrices[ref_id]))
    embedding = pca.transform(scaler.transform(common_matrices[ref_id]))
    classifier = KNeighborsClassifier(n_neighbors=15, weights='distance').fit(embedding, labels)
    payload = {'created_at': datetime.now(timezone.utc).isoformat(), 'datasets': [], 'shared_genes': len(common),
               'type_names': TYPE_NAMES, 'programs': {k: v[0] for k, v in PROGRAMS.items()},
               'validation': folds, 'gnn_status': 'not_trained', 'baseline_status': 'completed',
               'methods': {'mapping': '共享基因内归一化、标准化、PCA20、距离加权kNN15',
                           'scores': '每份数据内总计数归一化至10000、log1p后对覆盖基因取均值；至少3基因且覆盖率≥50%',
                           'niche': '排除中心细胞的12/24近邻组成与可测功能程序；以空间样本1拟合缩放和GMM，预测样本2',
                           'confidence': '分类支持度与GMM归属概率分别显示，均不作为校准置信度',
                           'sample_scope': '开发用子集；单细胞按类型抽样，空间为局部裁剪；患者字段缺失的空间数据按样本展示'}}
    type_order = sorted(set(labels)) + ['Uncertain']
    spatial_items = []
    for key, (item, matrix, genes, obs) in loaded.items():
        scores, coverage = program_scores(matrix, genes)
        data = {'id': key, 'modality': item['modality'], 'cells': len(obs), 'genes': len(genes),
                'cell_ids': obs.index.astype(str).tolist(), 'coverage': coverage,
                'program_scores': {k: round_list(v) for k, v in scores.items()}, 'type_order': type_order}
        export = pd.DataFrame(index=obs.index)
        if item['modality'] == 'scrna':
            data.update(name='肠癌单细胞 · GSE132465', coords=round_list(embedding[:, :2]),
                        labels=labels.tolist(), patients=patients.tolist(), coordinate_label='共有基因 PCA',
                        source='GSE132465', label_source='原作者细胞类型注释')
            export['patient_id'] = patients
            export['cell_type'] = labels
        else:
            progress(f'注释与建图：{key}')
            z = pca.transform(scaler.transform(common_matrices[key]))
            probabilities = classifier.predict_proba(z)
            support = probabilities.max(axis=1)
            predicted = classifier.classes_[probabilities.argmax(axis=1)].astype(object)
            predicted[support < .55] = 'Uncertain'
            xy = obs[['x', 'y']].to_numpy()
            data.update(name='Vizgen 肠癌 · ' + ('样本1' if 'Patient1' in key else '样本2'),
                        coords=round_list(xy, 3), labels=predicted.tolist(), support=round_list(support),
                        coordinate_label='来源空间坐标', source='Vizgen MERSCOPE FFPE',
                        label_source='单细胞共有基因 kNN 映射', patient_metadata='待来源资料确认', niche_models={})
            feature_groups = {}
            for k in [12, 24]:
                near = neighbors(xy, k)
                composition = np.column_stack([(predicted[near] == cell_type).mean(axis=1) for cell_type in type_order])
                available = [p for p in PROGRAMS if p in scores]
                local_programs = np.column_stack([scores[p][near].mean(axis=1) for p in available])
                feature_groups[k] = np.column_stack([composition, local_programs])
            spatial_items.append((data, feature_groups))
            export['x'], export['y'] = xy[:, 0], xy[:, 1]
            export['cell_type'] = predicted
            export['mapping_support'] = support
        for p, score in scores.items():
            export['score_' + p] = score
        export.to_csv(OUTPUT / f'{key}_annotations.tsv', sep='\t', index_label='cell_id')
        data['type_counts'] = pd.Series(data['labels']).value_counts().to_dict()
        data['score_summary'] = {p: {t: float(np.mean(np.asarray(score)[np.asarray(data['labels']) == t]))
                                    for t in set(data['labels'])} for p, score in scores.items()}
        payload['datasets'].append(data)
    progress('拟合并应用空间生态位基线')
    for neighbors_k in [12, 24]:
        train_features = spatial_items[0][1][neighbors_k]
        env_scaler = StandardScaler().fit(train_features)
        for clusters in [3, 4, 5, 6]:
            model = GaussianMixture(n_components=clusters, covariance_type='diag', n_init=3,
                                    max_iter=200, reg_covar=1e-4, random_state=42)
            model.fit(env_scaler.transform(train_features))
            for data, feature_groups in spatial_items:
                posterior = model.predict_proba(env_scaler.transform(feature_groups[neighbors_k]))
                data['niche_models'][f'{neighbors_k}_{clusters}'] = {
                    'labels': posterior.argmax(axis=1).tolist(), 'support': round_list(posterior.max(axis=1)),
                    'probabilities': round_list(posterior), 'converged': bool(model.converged_),
                    'train_sample': spatial_items[0][0]['id']}
                if neighbors_k == 12 and clusters == 4:
                    f = OUTPUT / f"{data['id']}_annotations.tsv"
                    obs_out = pd.read_csv(f, sep='\t', index_col=0)
                    obs_out['niche_baseline'] = posterior.argmax(axis=1) + 1
                    obs_out['niche_probability'] = posterior.max(axis=1)
                    obs_out.to_csv(f, sep='\t', index_label='cell_id')
    path = OUTPUT / 'analysis.json'
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf8')
    temporary.replace(path)
    progress('分析完成')
    return payload

if __name__ == '__main__':
    run(lambda message: print(message, flush=True))
