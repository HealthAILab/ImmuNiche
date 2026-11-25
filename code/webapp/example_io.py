"""Read NPZ inputs stored as one file or contiguous binary segments."""
from io import BytesIO
from pathlib import Path
from scipy import sparse


def load_counts(path):
    path = Path(path)
    if path.exists():
        return sparse.load_npz(path)
    parts = sorted(path.parent.glob(path.name + '.part[0-9][0-9][0-9]'))
    if not parts:
        raise FileNotFoundError(f'Counts not found: {path.name}')
    if [part.name for part in parts] != [f'{path.name}.part{i:03d}' for i in range(len(parts))]:
        raise ValueError('Count segments must be complete and contiguous')
    return sparse.load_npz(BytesIO(b''.join(part.read_bytes() for part in parts)))
