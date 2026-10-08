import json,glob,sys
want={ # cik: list of (form, filingDate prefix)  -- None = latest
 "320193":[("10-K",None),("10-K","2016"),("10-Q",None)],
 "19617":[("10-K",None),("10-Q",None)],
 "34088":[("10-K",None)],
 "78003":[("10-K",None)],
 "104169":[("10-K",None)],
 "1067983":[("10-K",None),("10-K","2017")],
 "21344":[("10-K",None)],
 "37996":[("10-K",None)],
 "106532":[("10-K",None),("10-K","2016"),("10-Q",None)],
 "40545":[("10-K",None),("10-K","2019")],
 "1065280":[("10-K",None)],
}
out=[]
for f in glob.glob(sys.argv[1]+"/*CIK*.json"):
    d=json.load(open(f,encoding="utf-8")); cik=str(int(d["cik"])); r=d["filings"]["recent"]
    for form,pref in want.get(cik,[]):
        for i in range(len(r["form"])):
            if r["form"][i]==form and (pref is None or r["filingDate"][i].startswith(pref)):
                acc=r["accessionNumber"][i]
                out.append(f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace("-","")}/{r["primaryDocument"][i]}')
                print(d["name"][:22].ljust(22),form,r["filingDate"][i],acc,r["primaryDocument"][i],"ixbrl" if r["isInlineXBRL"][i] else "html",file=sys.stderr); break
print(" ".join(out))
