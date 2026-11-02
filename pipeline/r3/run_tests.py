"""Run the four closeness tests on every (older, newer) witness pair of every text unit -> triplets.pkl."""
import os, json, pickle
from tests import all_triplets
HERE = os.path.dirname(os.path.abspath(__file__))
U = pickle.load(open(os.path.join(HERE, 'units.pkl'), 'rb'))
D = {x['key']: x for f in ('datings_A.json', 'datings_B.json') for x in json.load(open(os.path.join(HERE, f)))}
T = all_triplets(U, D)
pickle.dump(T, open(os.path.join(HERE, 'triplets.pkl'), 'wb'))
print(len(T), 'comparisons')
