import sys,re,csv
L={r[0]:r for r in csv.reader(open('labels2.tsv'),delimiter='\t')}
txt={}
import glob
for f in sorted(glob.glob('tb2_*.txt')):
    cur=None
    for line in open(f):
        m=re.match(r'### (T\d+) \| (.*)',line)
        if m: cur=m.group(1); txt[cur]=[m.group(2).strip()]; continue
        if cur and line.startswith(('OPP:','SRC:')): txt[cur].append(line.strip())
W=int(sys.argv[1])
for t in sys.argv[2:]:
    h,o,s=txt[t]
    cut=lambda x:' '.join(x.split()[:W])
    print(f'== {t} {h}\n  LABEL: {L[t][1]} | {L[t][2]} | {L[t][3]}\n  {cut(o)}\n  {cut(s)}')
