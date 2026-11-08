"""Offline E ranking regressions. No model downloads or API calls."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import lexicon_retrieval as lr

class DeterministicE(unittest.TestCase):
    def store(self, order, jitter=0.0):
        rows = pd.DataFrame([dict(user_id='P1', scene_id=f'scene_{i:02d}', register='chat',
            origin='survey', query_text='query', incoming='incoming', response=f'reply {i}',
            target_label='Agree', sender_role='friend', stakes='social') for i in order])
        with patch.object(lr, 'embed', lambda texts, which='semantic': np.tile([1., 0.], (len(texts), 1))):
            store = lr.ExampleStore(rows)
        # Opposite tiny perturbations must not reorder near-equal candidates or the top-15 pool.
        noise = np.array([1 if i % 2 else -1 for i in order]) * jitter
        store.sem[:, 0] += noise
        store.sty[:, 0] -= noise
        return store

    def get(self, store, k=3):
        with patch.object(lr, 'embed', lambda texts, which='semantic': np.tile([1., 0.], (len(texts), 1))):
            return store.retrieve('E_styledistance', 'P1', 'query', k=k, return_rows=True).scene_id.tolist()

    def test_row_order_and_near_ties(self):
        expected = [f'scene_{i:02d}' for i in range(3)]
        for order in (list(range(20)), list(reversed(range(20))), np.random.default_rng(1).permutation(20).tolist()):
            for jitter in (0., 1e-8, -1e-8):
                with self.subTest(order=order, jitter=jitter):
                    self.assertEqual(self.get(self.store(order, jitter)), expected)

    def test_semantic_shortlist_is_not_replaced_by_id_order(self):
        store = self.store(list(range(20)))
        store.sem[19] = [2., 0.]
        store.sty[19] = [2., 0.]
        self.assertEqual(self.get(store)[0], 'scene_19')

    def test_existing_b_and_c_keep_semantic_order(self):
        store = self.store(list(range(20)))
        store.sem[19] = [2., 0.]
        with patch.object(lr, 'embed', lambda texts, which='semantic': np.tile([1., 0.], (len(texts), 1))):
            for condition in ('B_semantic', 'C_context'):
                refs = store.retrieve(condition, 'P1', 'query', return_rows=True)
                self.assertEqual(refs.scene_id.iloc[0], 'scene_19')

    def test_clear_style_difference_is_preserved(self):
        store = self.store(list(range(10)))
        store.sty[9] = [2., 0.]
        self.assertEqual(self.get(store)[0], 'scene_09')

    def test_other_person_cannot_enter_pool(self):
        store = self.store(list(reversed(range(20))))
        store.df.loc[store.df.scene_id == 'scene_00', 'user_id'] = 'P2'
        self.assertNotIn('scene_00', self.get(store))

if __name__ == '__main__':
    unittest.main()
