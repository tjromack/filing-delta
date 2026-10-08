import sys, re, glob, os
from lxml import html, etree
BLOCK={"p","div","td","th","li","h1","h2","h3","h4","h5","h6","tr","table","br","center","font"}
HEAD=re.compile(r"^\s*(part\s+[iv]+[\s.,:\-—–]*)?item[\s\xa0]*(\d+[a-c]?)\s*[\.\:\-—–]?\s*(.{0,80})", re.I)
NAMED=re.compile(r"^\s*(risk factors|management['’]s discussion and analysis)", re.I)
def leaves(root):
    for el in root.iter():
        if not isinstance(el.tag,str): continue
        t=el.tag.split("}")[-1].lower()
        if t not in ("p","div","td","th","li","h1","h2","h3","h4","h5","h6"): continue
        if any(isinstance(c.tag,str) and c.tag.split("}")[-1].lower() in ("p","div","td","th","li","table","h1","h2","h3","h4") for c in el.iterdescendants()): continue
        yield el
def is_bold(el):
    for e in [el,*el.iterdescendants()]:
        if not isinstance(e.tag,str): continue
        s=(e.get("style") or "").replace(" ","").lower()
        if "font-weight:bold" in s or "font-weight:700" in s or e.tag.lower() in("b","strong"): return True
    return False
for f in sys.argv[1:]:
    raw=open(f,"rb").read()
    doc=html.fromstring(raw)
    for h in doc.xpath("//*[local-name()='header']"): h.getparent().remove(h)
    blocks=[]
    for el in leaves(doc):
        txt=re.sub(r"[\s\xa0]+"," ",el.text_content()).strip()
        if txt: blocks.append((el,txt))
    n=len(blocks); total=sum(len(t) for _,t in blocks)
    print(f"\n=== {os.path.basename(f)}  bytes={len(raw)} blocks={n} chars={total}")
    hrefs=[a.get("href") for a in doc.iter("a") if (a.get("href") or "").startswith("#")]
    print(f"   internal #links: {len(hrefs)}")
    cum=0
    for i,(el,t) in enumerate(blocks):
        m=HEAD.match(t); m2=NAMED.match(t)
        if (m and m.group(2).lower() in ("1a","2","7","7a","8","1b","3","1","9","4")) or (m2 and len(t)<90):
            anc=[a.tag for a in el.iterancestors() if isinstance(a.tag,str)]
            intable="table" in anc
            inA=el.xpath("ancestor-or-self::a | .//a[@href]")
            idanchor=bool(el.xpath("ancestor-or-self::*[@id] | .//*[@id] | .//a[@name]"))
            print(f"   {cum/total:5.3f} b{i:<5} {'TBL' if intable else '   '} {'BOLD' if is_bold(el) else '    '} {'LINK' if inA else '    '} {'ID' if idanchor else '  '} len={len(t):<5} {t[:95]!r}")
        cum+=len(t)
