"""Validate example input alignment and report shared measured features."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import sparse
from webapp.example_io import load_counts

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / 'data/local_example'
OUT = PROJECT / 'runs/example_input_check'

if __name__ == '__main__':
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf8'))
    report, gene_sets = [], {}
    for dataset in manifest['datasets']:
        x = load_counts(ROOT / dataset['counts'])
        genes = pd.read_csv(ROOT / dataset['genes'], sep='\t')['gene']
        obs = pd.read_csv(ROOT / dataset['observations'], sep='\t', index_col=0)
        assert x.shape == (len(obs), len(genes)), 'Shape mismatch'
        assert obs.index.is_unique, 'Duplicate cell IDs'
        assert genes.is_unique, 'Duplicate gene names'
        assert np.isfinite(x.data).all() and (x.data >= 0).all(), 'Invalid counts'
        assert np.equal(x.data, np.floor(x.data)).all(), 'Fractional raw counts'
        if dataset['modality'] == 'spatial':
            assert np.isfinite(obs[['x', 'y']].to_numpy()).all(), 'Invalid coordinates'
        gene_sets[dataset['dataset_id']] = set(genes)
        report.append({'dataset_id': dataset['dataset_id'], 'cells': len(obs), 'genes': len(genes),
                       'zero_count_cells': int((np.asarray(x.sum(axis=1)).ravel() == 0).sum()),
                       'cell_types': obs['cell_type_reference'].value_counts().to_dict() if 'cell_type_reference' in obs else None})
    shared = set.intersection(*gene_sets.values())
    OUT.mkdir(parents=True, exist_ok=True)
    pd.Series(sorted(shared), name='gene').to_csv(OUT / 'shared_genes.tsv', sep='\t', index=False)
    result = {'datasets': report, 'shared_genes_all': len(shared), 'matrix_alignment': 'passed'}
    (OUT / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(result, ensure_ascii=True))
