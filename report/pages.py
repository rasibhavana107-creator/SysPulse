import subprocess, json, re
pdf="report/SysPulse_Mini_Project_Report.pdf"
n=int(re.search(r"Pages:\s+(\d+)",subprocess.run(["pdfinfo",pdf],capture_output=True,text=True).stdout).group(1))
txt=[subprocess.run(["pdftotext","-f",str(i),"-l",str(i),"-layout",pdf,"-"],capture_output=True,text=True).stdout for i in range(1,n+1)]
keys=json.load(open("report/toc_keys.json")); res={}
intro=next(i for i,t in enumerate(txt,1) if i>3 and re.search(r"^\s*INTRODUCTION\s*$",t,re.M))
for k,v in keys.items():
    for i,t in enumerate(txt,1):
        if i<=intro-1: continue
        if re.search(r"^\s*"+re.escape(v)+r"\s*$",t,re.M): res[v]=i-(intro-1); break
    else: print("missing",v)
json.dump(res,open("report/pages.json","w"),indent=1); print(res, "total", n)
