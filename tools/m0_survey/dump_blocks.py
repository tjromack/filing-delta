import sys,re
from lxml import html
f=sys.argv[1]; a,b=int(sys.argv[2]),int(sys.argv[3])
doc=html.fromstring(open(f,"rb").read())
for h in doc.xpath("//*[local-name()='header']"): h.getparent().remove(h)
TAGS=("p","div","td","th","li","h1","h2","h3","h4","h5","h6")
bl=[]
for el in doc.iter():
    if not isinstance(el.tag,str) or el.tag.split("}")[-1].lower() not in TAGS: continue
    if any(isinstance(c.tag,str) and c.tag.split("}")[-1].lower() in TAGS+("table",) for c in el.iterdescendants()): continue
    t=re.sub(r"[\s\xa0]+"," ",el.text_content()).strip()
    if t: bl.append(t)
for i in range(max(0,a),min(b,len(bl))): print(f"b{i}: {bl[i][:220]}".encode("ascii","replace").decode())
