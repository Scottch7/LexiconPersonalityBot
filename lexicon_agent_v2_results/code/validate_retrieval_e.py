"""Local frozen-split validation; use fresh processes to compare thread counts."""
import os
# Set HF_HUB_OFFLINE=1 externally once the public embedding models are cached.
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
import argparse, json, hashlib
from pathlib import Path
import pandas as pd
import torch
from lexicon_retrieval import ExampleStore

p = argparse.ArgumentParser()
p.add_argument('--threads', type=int, default=1)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
torch.set_num_threads(a.threads)
root = Path(__file__).resolve().parents[1]
result = {}
for uid in ('P1', 'P2'):
    split = json.loads((root / f'frozen/split_{uid}_seed1.json').read_text())['test_scene_ids']
    store = ExampleStore.from_survey(root / f'data/{uid}_responses.csv', root / 'data/prompt_bank_v2.csv', exclude_scene_ids=split)
    assert not store.df.scene_id.isin(split).any()
    assert store.df.user_id.eq(uid).all()
    assert store.df.register.eq('chat').all()
    tests = pd.read_csv(root / f'data/{uid}_responses.csv')
    tests = tests[tests.scene_id.isin(split) & tests.register.eq('chat')]
    assert len(tests) == 40
    for row in tests.itertuples():
        refs = store.retrieve('E_styledistance', uid, row.shown_message, k=3, return_rows=True)
        assert len(refs) == 3 and refs.user_id.eq(uid).all()
        assert not refs.scene_id.isin(split).any()
        result[f'{uid}/{row.scene_id}'] = refs.scene_id.tolist()
    assert store.retrieve('E_styledistance', 'nobody', 'query') == []
a.output.write_text(json.dumps(result, sort_keys=True, indent=2))
print('Validated queries:', len(result), 'threads:', a.threads,
      'SHA256:', hashlib.sha256(a.output.read_bytes()).hexdigest())
