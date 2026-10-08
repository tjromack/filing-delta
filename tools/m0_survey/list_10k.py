import json,sys,glob
for f in sorted(glob.glob(sys.argv[1]+"/*CIK*.json")):
    d=json.load(open(f,encoding="utf-8"))
    r=d["filings"]["recent"]
    rows=[(r["filingDate"][i],r["form"][i],r["accessionNumber"][i],r["primaryDocument"][i],r["isInlineXBRL"][i],r["reportDate"][i]) for i in range(len(r["form"])) if r["form"][i] in("10-K","10-K405","10-KT")]
    print(d["cik"],d["name"],"| fy end",d.get("fiscalYearEnd"),"| recent oldest",r["filingDate"][-1],"| older files",len(d["filings"]["files"]))
    for x in rows: print("   ",*x)
