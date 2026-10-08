import sys,re,os
from lxml import html
KEY=re.compile(r"(item\s*1a|risk\s+factors|item\s*7\b|item\s*2\b|management.s\s+discussion)",re.I)
for f in sys.argv[1:]:
    doc=html.fromstring(open(f,"rb").read())
    ids={}
    for i,el in enumerate(doc.iter()):
        if not isinstance(el.tag,str): continue
        for k in (el.get("id"),el.get("name") if el.tag=="a" else None):
            if k: ids.setdefault(k,i)
    order={el:i for i,el in enumerate(doc.iter())}
    total=len(order)
    hits=[]
    for a in doc.iter("a"):
        h=a.get("href") or ""
        if not h.startswith("#"): continue
        # text of the TOC row containing the link
        row=a
        for anc in a.iterancestors():
            if anc.tag=="tr": row=anc;break
        t=re.sub(r"[\s\xa0]+"," ",row.text_content()).strip()
        if KEY.search(t) and len(t)<160:
            tgt=ids.get(h[1:])
            hits.append(f"{t[:70]!s:72} -> {'MISSING' if tgt is None else f'{tgt/total:.3f}'}")
    seen=[];[seen.append(x) for x in hits if x not in seen]
    print(f"== {os.path.basename(f)} links={sum(1 for a in doc.iter('a') if (a.get('href') or '').startswith('#'))}")
    for x in seen[:8]: print("   ",x.encode('ascii','replace').decode())
