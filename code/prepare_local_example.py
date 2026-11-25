"""Create small example inputs from local public matrices, retaining source IDs."""
from pathlib import Path
import argparse
import csv
import gzip
import json
import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
DEST = Path(__file__).resolve().parents[1] / 'data/local_example'
SCRNA_SOURCE = ROOT / 'data/raw/GSE132465'
SPATIAL_SOURCE = ROOT / 'data/raw/vizgen'

def write_dataset(name, counts, genes, obs):
    if counts.shape != (len(obs), len(genes)) or not obs.index.is_unique:
        raise ValueError('Invalid matrix/metadata alignment')
    if not np.isfinite(counts.data).all() or (counts.data < 0).any():
        raise ValueError('Invalid counts')
    expressed = np.asarray(counts.sum(axis=1)).ravel() > 0
    counts = counts[expressed]
    obs = obs.iloc[np.flatnonzero(expressed)].copy()
    target = DEST / name
    target.mkdir(parents=True, exist_ok=True)
    sparse.save_npz(target / 'counts.npz', counts.tocsr())
    pd.Series(genes, name='gene').to_csv(target / 'genes.tsv', sep='\t', index=False)
    obs.to_csv(target / 'cells.tsv', sep='\t', index_label='cell_id')
    print(json.dumps({'dataset': name, 'cells': len(obs), 'genes': len(genes), 'nonzero': counts.nnz}), flush=True)

def prepare_scrna():
    source = SCRNA_SOURCE
    meta = pd.read_csv(source / 'GSE132465_GEO_processed_CRC_10X_cell_annotation.txt.gz', sep='\t', index_col=0)
    selected = []
    for patient in ['SMC07', 'SMC09']:
        local = meta[(meta.Patient == patient) & (meta.Class == 'Tumor')]
        # Keep all cell types; sample reproducibly within type for a compact demo.
        for _, group in local.groupby('Cell_type'):
            selected.extend(group.sample(n=min(350, len(group)), random_state=42).index)
    obs = meta.loc[selected].copy()
    genes, rows = [], []
    with gzip.open(source / 'GSE132465_GEO_processed_CRC_10X_raw_UMI_count_matrix.txt.gz', 'rt') as handle:
        header = next(csv.reader([next(handle)], delimiter='\t'))
        if header[0] not in meta.index:
            header = header[1:]
        positions = pd.Index(header).get_indexer(selected)
        if (positions < 0).any():
            raise ValueError('Selected scRNA cell missing from matrix')
        selected_columns = (positions + 1).tolist()
        for line in handle:
            fields = line.rstrip('\r\n').split('\t')
            if len(fields) != len(header) + 1:
                raise ValueError(f'Matrix width mismatch: {fields[0]}')
            values = np.fromstring('\t'.join(fields[j] for j in selected_columns), sep='\t')
            if len(values) != len(selected):
                raise ValueError(f'Subset width mismatch: {fields[0]}')
            genes.append(fields[0].strip('"'))
            rows.append(sparse.csr_matrix(values.reshape(1, -1)))
    matrix = sparse.vstack(rows, format='csr').T.tocsr()
    obs['patient_id'] = obs.Patient
    obs['sample_id'] = obs.Sample
    obs['cell_type_reference'] = obs.Cell_type
    obs['cell_state_reference'] = obs.Cell_subtype
    obs['reference_role'] = 'evaluation_or_annotation_reference'
    write_dataset('scrna_crc', matrix, genes, obs)

def prepare_spatial(sample):
    source = SPATIAL_SOURCE
    meta = pd.read_csv(source / f'{sample}_cell_metadata.csv', index_col=0)
    if not meta.index.is_unique:
        raise ValueError('Duplicated spatial cell IDs')
    xy = meta[['center_x', 'center_y']].to_numpy()
    if not np.isfinite(xy).all():
        raise ValueError('Invalid spatial coordinates')
    center = np.median(xy, axis=0)
    distance = ((xy-center)**2).sum(axis=1)
    # Contiguous local crop preserves neighborhoods; avoid random spatial sampling.
    ids = meta.index[np.argsort(distance)[:4000]]
    blocks, order, genes = [], [], None
    for frame in pd.read_csv(source / f'{sample}_cell_by_gene.csv', index_col=0, chunksize=20000):
        selected = frame.loc[frame.index.isin(ids)]
        if selected.empty:
            continue
        values = selected.to_numpy(dtype=np.float32)
        if not np.isfinite(values).all() or (values < 0).any() or not np.equal(values, np.floor(values)).all():
            raise ValueError(f'Invalid selected raw counts: {sample}')
        genes = selected.columns.tolist()
        blocks.append(sparse.csr_matrix(values))
        order.extend(selected.index.tolist())
    if len(order) != len(ids) or len(set(order)) != len(ids):
        raise ValueError('Spatial expression/metadata IDs do not match')
    obs = meta.loc[order].copy()
    obs['sample_id'] = sample
    obs['patient_id'] = ''
    obs['x'] = obs.center_x
    obs['y'] = obs.center_y
    matrix = sparse.vstack(blocks, format='csr')
    controls = np.array([g.startswith('Blank-') for g in genes])
    obs['blank_control_counts'] = np.asarray(matrix[:, controls].sum(axis=1)).ravel()
    write_dataset(sample, matrix[:, ~controls], [g for g, control in zip(genes, controls) if not control], obs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scrna-dir', type=Path, default=SCRNA_SOURCE)
    parser.add_argument('--spatial-dir', type=Path, default=SPATIAL_SOURCE)
    parser.add_argument('--output', type=Path, default=DEST)
    args = parser.parse_args()
    SCRNA_SOURCE, SPATIAL_SOURCE, DEST = args.scrna_dir, args.spatial_dir, args.output
    DEST.mkdir(parents=True, exist_ok=True)
    prepare_scrna()
    for name in ['HumanColonCancerPatient1', 'HumanColonCancerPatient2']:
        prepare_spatial(name)
    template = ROOT / 'data/local_example/manifest.json'
    if template.exists() and template.resolve() != (DEST / 'manifest.json').resolve():
        (DEST / 'manifest.json').write_text(template.read_text(encoding='utf8'), encoding='utf8')
