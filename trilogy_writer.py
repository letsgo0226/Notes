#!/usr/bin/env python3
"""Incremental scholarly trilogy drafts. Requires an authorized chat-completions model."""
import json,os,pathlib,urllib.request,re,sys
root=pathlib.Path(__file__).resolve().parent
out=root/"Notes"/"reading-trilogy"
statefile=out/"state.json"
books=[
("01_Caduceus_如何閱讀一本書","Caduceus：如何閱讀一本書","Everything real is potentially accessible through spiritual energy.",["閱讀的困難與可能性","實在與精神參與","笛卡兒與懷疑","Caduceus 與理性","文本與理解","反例與可接近性的界限","閱讀的方法","結論"]),
("02_Hu_Mantra_如何閱讀自己","Hu Mantra：如何閱讀自己","Human transformation can be achieved through consistent spiritual practice.",["自我與時間","Hu Mantra 的象徵","一致性與習慣","練習與修正","思想實驗","反例與限制","自我理解","結論"]),
("03_Love_如何閱讀生命","Love Is The Solution For Everything：如何閱讀生命","Love is the highest actualization of spiritual energy in the realization of the Higher Self.",["閱讀生命","精神能量的定義","愛與最高實現","Higher Self","愛與求真","目的論論證","反對意見","閱讀生命的實踐","總結"])]
state=json.loads(statefile.read_text()) if statefile.exists() else {"book":0,"chapter":0,"part":0,"completed":[]}
b,c,p=(state[k] for k in ("book","chapter","part"))
if b>=len(books): print("All planned sections generated; human review remains.");sys.exit()
slug,title,thesis,chapters=books[b]
target=out/slug/("%02d"%(c+1)+"_"+chapters[c])/("part_%02d.md"%(p+1))
if "--plan" in sys.argv: print(target.relative_to(root));sys.exit()
if target.exists():sys.exit("Refusing to overwrite existing section")
token=os.getenv("WRITER_API_KEY") or os.getenv("GITHUB_TOKEN")
if not token:sys.exit("No API token; no generation performed")
context=[]
for f in sorted((root/"Notes").glob("*")):
 if f.is_file() and f.stat().st_size<100000 and f.suffix in ("",".txt",".md"):
  t=f.read_text(errors="replace")
  hits=[line.strip() for line in t.splitlines() if any(w in line for w in ("閱讀","哲學","Love","精神","形上"))]
  if hits:context.append({"source":f.name,"excerpt":" ".join(hits[:3])[:400]})
context=context[:10]
prior=sorted(target.parent.glob("part_*.md")) if target.parent.exists() else []
previous=prior[-1].read_text()[-900:] if prior else ""
prompt=f"""以繁體中文撰寫哲學專書《{title}》第{c+1}章「{chapters[c]}」第{p+1}/5節的完整連續正文（至少900中文字），不可僅列大綱。中心命題：{thesis}。依序展開問題、論證、思想實驗、反例、綜合；本節應有獨立進展。前文：{previous}。本地參考片段（未驗證，勿假造引用）：{json.dumps(context,ensure_ascii=False)}。不得將愛的最高頻率當成已證實的物理量；區分假設、定義、證據與推論。不得虛構來源或書目。"""
payload=json.dumps({"model":os.getenv("WRITER_MODEL") or "openai/gpt-4.1-mini","messages":[{"role":"system","content":"你是嚴謹的繁體中文哲學書籍作者。請寫實質章節正文而非大綱；不虛構來源。"},{"role":"user","content":prompt}],"max_tokens":3500,"temperature":0.55},ensure_ascii=False).encode()
url=os.getenv("WRITER_API_URL") or "https://models.github.ai/inference/chat/completions"
req=urllib.request.Request(url,data=payload,headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
with urllib.request.urlopen(req,timeout=120) as response: result=json.load(response)
draft=result["choices"][0]["message"]["content"].strip()
n=len(re.findall(r"[\u4e00-\u9fff]",draft))
if n<600:sys.exit("Quality gate failed: too short, state unchanged")
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text("<!-- UNREVIEWED AI DRAFT: facts, sources and arguments require verification -->\n\n"+draft+"\n",encoding="utf-8")
state["completed"].append({"file":str(target.relative_to(root)),"han_chars":n})
p+=1
if p==5:
 p=0;c+=1
 if c==len(chapters):b+=1;c=0
state.update(book=b,chapter=c,part=p)
out.mkdir(parents=True,exist_ok=True)
statefile.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
print("Generated",target.relative_to(root),n)
