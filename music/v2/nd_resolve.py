"""Resolve Naked Drums sample names (RR1-4) per group/articulation.
usage: python -I nd_resolve.py <Data dir> <group name> [...]  -> lines: group label sample"""
import re, sys, os
data = sys.argv[1]
def defs(path):
    d = {}
    for line in open(path, encoding="latin-1"):
        m = re.match(r'\s*#define\s+(\$\w+)\s+(\S+)', line)
        if m: d[m.group(1)] = m.group(2)
    return d
def emit(g, lab, f, r):
    d = defs(os.path.join(data, f))
    rr = None
    for line in open(os.path.join(data, r), encoding="latin-1"):
        m = re.match(r'#define \$RR (\w+)', line)
        if m: rr = m.group(1)
        m = re.search(r'sample=(\S+)', line)
        if m and rr in ("one", "two", "three", "four"):
            s = m.group(1).replace("$RR", rr).replace(".$ext", ".flac")
            for k in sorted(d, key=len, reverse=True):
                s = s.replace(k, d[k])
            print(g, lab, s)
for g in sys.argv[2:]:
    txt = open(os.path.join(data, "group", g + ".txt"), encoding="latin-1").read()
    for blk in re.split(r'<group>', txt)[1:]:
        lab = re.search(r'group_label=(\S+)', blk)
        fi = re.search(r'"\.\./Data/(file/\w+\.txt)"', blk)
        ri = re.search(r'"\.\./Data/(region/\w+\.txt)"', blk)
        if fi and ri:
            emit(g, lab.group(1) if lab else "?", fi.group(1), ri.group(1))
