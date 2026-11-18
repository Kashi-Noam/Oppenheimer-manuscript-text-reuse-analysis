"""Run the four closeness tests on every (older, newer) witness pair of every text unit -> triplets.pkl."""
import os, json, pickle
from tests import all_triplets
from mode import SUF, datings
HERE = os.path.dirname(os.path.abspath(__file__))
U = pickle.load(open(os.path.join(HERE, f'units{SUF}.pkl'), 'rb'))
D = datings()
T = all_triplets(U, D)
pickle.dump(T, open(os.path.join(HERE, f'triplets{SUF}.pkl'), 'wb'))
print(len(T), 'comparisons')
