"""Which data the matryoshka run uses.
OPP_MODE=thr (default): only matches with S >= 21.14 (the logistic-regression threshold).
OPP_MODE=all: every candidate that ACT aligned in full (2,650), with no threshold.
Outputs of the 'all' run carry the suffix _all (units_all.pkl, triplets_all.pkl, matryoshka_all.json, ...)."""
import os, json
MODE = os.environ.get('OPP_MODE', 'thr')
assert MODE in ('thr', 'all'), MODE
SUF = '' if MODE == 'thr' else '_all'
HERE = os.path.dirname(os.path.abspath(__file__))
DATING_FILES = ['datings_A.json', 'datings_B.json', 'datings_C.json', 'datings_D.json']

def datings():
    return {x['key']: x for f in DATING_FILES if os.path.exists(os.path.join(HERE, f)) for x in json.load(open(os.path.join(HERE, f), encoding='utf-8'))}
