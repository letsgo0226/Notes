#!/usr/bin/env python3
"""Finite HSI OriginalXY Turing-machine-driven research writer: NO AI models.

All 12 files of the locked Notes corpus are audited and fingerprinted. Only the
pinned, readable TM reference is executed with bounded steps, in a temp dir.
Crossref bibliographic metadata is optional; no copyrighted full text is copied.
The outputs are NOT original philosophical books or proven philosophical claims.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from hsi_notes_review import audit

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "books" / "reading-trilogy" / "open-corpus"
LOCK = ROOT / "hsi_notes_review.lock.json"
TM_SOURCE = "Notes/HSI_Prime_Analytic_2KB_Release/OriginalXY_reference.py"
PROTOCOL = "HSI-TM-OPEN-CORPUS-WRITER/1.0"
TM_LIMIT = 16
TM_BUDGET = 12
BOOKS = (
 ("01_Caduceus_如何閱讀一本書","Caduceus：如何閱讀一本書",
  "Everything real is potentially accessible through spiritual energy.",
  ("閱讀的困難與可能性","實在與精神參與","笛卡兒與懷疑","Caduceus 與理性",
   "文本與理解","反例與可接近性的界限","閱讀的方法","結論"),
  "philosophical hermeneutics reading epistemology"),
 ("02_Hu_Mantra_如何閱讀自己","Hu Mantra：如何閱讀自己",
  "Human transformation can be achieved through consistent spiritual practice.",
  ("自我與時間","Hu Mantra 的象徵","一致性與習慣","練習與修正",
   "思想實驗","反例與限制","自我理解","結論"),
  "self transformation habit reflective practice philosophy"),
 ("03_Love_如何閱讀生命","Love Is The Solution For Everything：如何閱讀生命",
  "Love is the highest actualization of spiritual energy in the realization of the Higher Self.",
  ("閱讀生命","精神能量的定義","愛與最高實現","Higher Self","愛與求真",
   "目的論論證","反對意見","閱讀生命的實踐","總結"),
  "ethics of care love virtue ethics flourishing"),
)
MODES = ("概念澄清","條件性論證","思想實驗","反例檢驗","實踐連結")
MODE_TEXT = (
 "首先區分概念的工作定義、語詞的日常意義與尚待證實的經驗命題。"
 "精神能量在此僅為精神參與能力的理論名稱，不能直接視為可用焦耳測量的物理量。",
 "若論證的前提尚未獲得獨立支持，結論只能具有條件性的效力。"
 "由一次理解困難的文本轉為可能理解，無法推出所有實在必然可被理解。",
 "可以設想一位讀者起初無法掌握陌生的文本；透過重新閱讀、請教與修正後，"
 "理解有所增進。此思想實驗檢查可變性，但不是一項受控制的因果實驗。",
 "必須考慮反例：持續練習也可能強化偏見，愛的宣稱也可能成為拒絕批判的藉口。"
 "因此，若缺少求真、證據與自我修正，三部曲的主張便不能獲得合理辯護。",
 "閱讀書本主要是解釋已有文本，閱讀生命同時涉及反省和行動。"
 "自我實現並非不受社會、身體與偶然事件限制的全能過程。"
)
QUESTIONS = (
 "閱讀中的目前無知，是否與不可理解相同？",
 "持續練習在什麼條件下才構成真正的轉化？",
 "將愛稱為最高實現，是否需要獨立的價值前提？",
 "人如何區分對文本的詮釋與對世界的知識？",
)

def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",",":")).encode("utf-8")

def digest(x):
    return hashlib.sha256(x).hexdigest()

def inventory():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    inv=audit(ROOT,lock)
    expected={x["path"] for x in lock["entries"]}
    if inv["inventory_status"]!="SOURCE_INVENTORY_VERIFIED" or len(expected)!=12:
        raise RuntimeError("Locked Notes source audit failed: "+str(inv["issues"]))
    if expected!=set(inv["observed"]) or TM_SOURCE not in expected:
        raise RuntimeError("Pinned twelve-source inventory differs from the repository")
    return lock,inv

def chapters():
    return [(slug,title,thesis,j,heading,query)
            for slug,title,thesis,sections,query in BOOKS
            for j,heading in enumerate(sections,1)]

def fresh_state():
    return {"protocol":PROTOCOL,"completed":[],"tm_word":None}

def load_state(folder=OUT):
    p=folder/"state.json"
    state=json.loads(p.read_text(encoding="utf-8")) if p.is_file() else fresh_state()
    if state.get("protocol")!=PROTOCOL or not isinstance(state.get("completed"),list):
        raise ValueError("Unrecognized writer state")
    return state

def machine(word, previous=None):
    """Actual locked OriginalXY reference, with 16 finite enumerated records."""
    with tempfile.TemporaryDirectory(prefix="hsi-trilogy-tm-") as temp:
        statefile=Path(temp)/"state.json"
        if previous is not None:
            if previous.get("w")!=word or previous.get("v")!=2 or not isinstance(previous.get("n"),int):
                raise RuntimeError("Incompatible TM checkpoint/input")
            statefile.write_bytes(canon(previous))
        env={"PATH":os.environ.get("PATH",""),"PYTHONIOENCODING":"utf-8",
             "HSI_WORD":word,"HSI_LIMIT":str(TM_LIMIT),"HSI_BUDGET":str(TM_BUDGET),
             "HSI_SLEEP":"0","HSI_STATE":str(statefile),"HSI_TRACE":"0"}
        process=subprocess.run([sys.executable,"-I",str(ROOT/TM_SOURCE)],
                               cwd=temp,env=env,capture_output=True,text=True,
                               check=True,timeout=25)
        trace=[json.loads(line) for line in process.stdout.splitlines() if line.strip()]
        checkpoint=json.loads(statefile.read_text(encoding="utf-8"))
    if len(trace)!=TM_LIMIT or any(
        x.get("protocol")!="HSI-ORIGINAL-XY/2K" or
        x.get("status") not in ("HALTED","UNRESOLVED","SKIPPED_BUDGET")
        for x in trace
    ):
        raise RuntimeError("Incomplete or invalid finite TM trace")
    if checkpoint.get("w")!=word or checkpoint.get("t")!=0:
        raise RuntimeError("TM checkpoint validation failed")
    # The actual machine trace, not a random number or a hash of the book title,
    # determines the next uncompleted chapter and its editorial mode.
    selector=int(digest(canon(trace))[:16],16)
    return trace,checkpoint,selector

class LockedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urllib.parse.urlsplit(newurl)
        if parsed.scheme!="https" or parsed.hostname!="api.crossref.org":
            raise ValueError("Unexpected Crossref redirect")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def crossref_metadata(query,offline=False,fetcher=None):
    if offline:
        return {"status":"OFFLINE","records":[],"query":query}
    url="https://api.crossref.org/works?"+urllib.parse.urlencode({
        "query.bibliographic":query,"rows":"4",
        "select":"DOI,title,author,published,URL,type",
    })
    request=urllib.request.Request(url,headers={
        "User-Agent":"HSI-TM-Open-Corpus/1.0 (https://github.com/letsgo0226/Notes)",
        "Accept":"application/json"})
    fetcher=fetcher or urllib.request.build_opener(LockedRedirect()).open
    try:
        with fetcher(request,timeout=20) as response:
            raw=response.read(250001)
        if len(raw)>250000:
            raise ValueError("Response too large")
        rows=json.loads(raw.decode("utf-8"))["message"]["items"][:4]
        refs=[]
        for item in rows:
            doi=str(item.get("DOI") or "").strip()
            title=(item.get("title") or [""])[0]
            if not doi.startswith("10.") or not isinstance(title,str) or not title.strip():
                continue
            names=[(" ".join(filter(None,(a.get("given"),a.get("family"))))).strip()
                   for a in (item.get("author") or [])[:3] if isinstance(a,dict)]
            dates=(item.get("published") or {}).get("date-parts") or []
            year=dates[0][0] if dates and dates[0] else None
            refs.append({"doi":doi[:200],"title":title.strip()[:400],
                         "authors":names,"year":year,
                         "url":"https://doi.org/"+urllib.parse.quote(doi,safe="/"),
                         "verified_scope":"depositor bibliographic metadata only"})
        return {"status":"FOUND" if refs else "EMPTY","query":query,
                "request_url":url,"records":refs}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        return {"status":"UNAVAILABLE","query":query,"request_url":url,
                "error":str(exc)[:180],"records":[]}

def quotes():
    """Four short, exact source excerpts; remaining eight files are hashed."""
    results=[]
    for label in ("1","2","3","4"):
        path=ROOT/"Notes"/label
        lines=path.read_text(encoding="utf-8").splitlines()
        found=next(((i+1,line.strip()) for i,line in enumerate(lines)
                    if i>8 and 24<=len(line.strip())<=180 and
                    any(k in line for k in ("有限","框架","系統","原理","一致性","對應"))),
                   (1,lines[0]))
        results.append({"path":"Notes/"+label,"line":found[0],"excerpt":found[1][:120]})
    return results

def make_text(ch,mode,excerpts,research,fingerprint):
    slug,title,thesis,num,heading,_=ch
    s=[
      "# %s｜第 %d 章：%s"%(title,num,heading),"",
      "本檔案是由有限圖靈機與顯式文字規則產生的研究札記；不是完整書籍正文、學術真理證明或已審訂的出版稿。","",
      "## 問題背景與概念界限","",
      "本章以「%s」為考察中心，所屬著作的核心待證成命題為：%s。"
      "無論使用何種技術作為程序引擎，哲學研究都須區分工作定義、經驗主張、"
      "規範主張及由前提到結論的有效推理。讀者是否暫時無法理解某一問題，"
      "與該問題在邏輯上不可理解，是兩種不同的斷言。"%(heading,thesis),"",
      "## 圖靈機指派的本次論證重點","",
      "本次有限枚舉所選的重點為「%s」：%s"%(MODES[mode],MODE_TEXT[mode]),"",
      "我們據此提出一項供作者檢查的問題：「%s」"
      "這個問題並非由圖靈機理解文義後提出；它來自公開、固定的編輯規則。"
      "選取程序的可重現性，不能當作該問題已被哲學上解決的證據。"%QUESTIONS[(num+mode)%len(QUESTIONS)],"",
      "## 從固定前提得到的有限結論","",
      "如果某位閱讀者經由恰當的準備與反覆檢查而真正理解某個段落，"
      "可以合理推論該段落在那些條件下對該閱讀者並非不可理解；"
      "但不能由此推論所有實在皆可被所有人理解。"
      "如果持續實踐伴隨適切回饋，則可能促進習慣或理解能力的變化；"
      "但若缺乏反思，持續性也可能強化錯誤。"
      "如果倫理理想已由獨立理由重視關懷、求真與責任，"
      "那麼愛可以作為候選的最高實現形式；然而這仍是需要比較與辯護的規範假說。","",
      "## 可追溯的 Notes 原始研究材料","",
      "以下是資料庫的簡短逐字摘錄。這些材料屬於數學、計算與形式方法研究，"
      "不被當作關於愛、靈性或讀書效果的實驗證據。",""
    ]
    for x in excerpts:
        s.append("- %s 第 %d 行：「%s」"%(x["path"],x["line"],x["excerpt"]))
    s+=["","鎖定清單中全部 12 個檔案均納入雜湊檢查。除上述四份文字材料之外，"
        "程式、證書與規格檔保留為可追溯的計算背景，不複製其程式碼為哲學論述。","",
        "## 公開學術資源題錄（尚待閱讀全文）",""]
    if research["records"]:
        for i,x in enumerate(research["records"],1):
            s.append("%d. %s（%s），《%s》，%s。此處僅使用 Crossref 題錄資料，不聲稱已閱讀或引用全文。"
                     %(i,", ".join(x["authors"]) or "作者未提供",
                       x["year"] or "日期未提供",x["title"],x["url"]))
    else:
        s.append("本次未取得可核對的題錄（狀態：%s），故不捏造文獻。"%research["status"])
    s+=["","## 後續研究與明確限制","",
        "以上文字可以作為章節撰寫的研究材料，不能視為具有獨創性、充分文獻"
        "閱讀及非循環論證的完整專書正文。真正的學術寫作仍需要作者閱讀原典、"
        "處理反對意見、查證文獻、比較思想史脈絡與進行修訂。",
        "Spirit、Spiritual Energy、Higher Self 等用語尚須清楚定義；"
        "「最高頻率」不得冒稱已經通過物理測量。","",
        "## 驗證參照","",
        "- 演算法：OriginalXY 有限圖靈機列舉與固定文字規則。",
        "- 來源索引 SHA-256："+fingerprint,
        "- 詳見同目錄的 manifest.json 與 tm_trace.json。",""]
    return "\n".join(s)

def build(offline=False,output=OUT):
    output=Path(output)
    lock,inv=inventory()
    state=load_state(output)
    completed={(r["book"],r["chapter"]) for r in state["completed"]}
    pending=[ch for ch in chapters() if (ch[0],ch[3]) not in completed]
    if not pending:
        print("DONE: research dossiers complete; books remain unwritten")
        return None
    fingerprint=digest(canon(inv["observed"]))
    word="".join(f"{b:08b}" for b in bytes.fromhex(fingerprint[:4]))
    if state.get("tm_word") not in (None,word):
        raise RuntimeError("Locked corpus changed: TM word mismatch")
    rows,checkpoint,selector=machine(word,state.get("tm_checkpoint"))
    chapter=pending[selector%len(pending)]
    mode=(selector//len(pending))%len(MODES)
    slug,_,_,number,heading,query=chapter
    dirname="%02d_"%number+re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]","_",heading)
    path=output/slug/dirname
    if path.exists():
        raise RuntimeError("Cannot overwrite existing research: "+str(path))
    research=crossref_metadata(query+" "+heading,offline=offline)
    excerpts=quotes()
    content=make_text(chapter,mode,excerpts,research,fingerprint)
    path.mkdir(parents=True)
    (path/"dossier.md").write_text(content,encoding="utf-8")
    (path/"tm_trace.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    manifest={
       "protocol":PROTOCOL,"status":"RULE_GENERATED_RESEARCH_UNREVIEWED",
       "model_calls":0,"full_text_read":False,"publication_ready":False,
       "source_commit":lock["source_commit"],"verified_source_count":len(inv["observed"]),
       "source_fingerprint_sha256":fingerprint,"source_inventory":inv["observed"],
       "tm_source":TM_SOURCE,"tm_trace_sha256":digest(canon(rows)),
       "tm_statuses":[r["status"] for r in rows],"tm_steps":len(rows),
       "tm_selected_mode":MODES[mode],"chapter":number,"book":slug,
       "web_research":research,"source_excerpts":excerpts,
       "dossier_sha256":digest(content.encode("utf-8"))
    }
    (path/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state["completed"].append({"book":slug,"chapter":number,"folder":str(path.relative_to(output))})
    state.update(tm_word=word,tm_checkpoint=checkpoint)
    output.mkdir(parents=True,exist_ok=True)
    (output/"state.json").write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("GENERATED",path.relative_to(ROOT) if output==OUT else path,
          "TM",MODES[mode],"Crossref",research["status"],"AI 0")
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan",action="store_true")
    mode.add_argument("--build",action="store_true")
    p.add_argument("--offline",action="store_true")
    args=p.parse_args()
    if args.plan:
        state=load_state()
        print(json.dumps({"protocol":PROTOCOL,"pending":len(chapters())-len(state["completed"]),
                          "choice":"locked finite TM trace","AI":False},ensure_ascii=False))
        return 0
    build(offline=args.offline)
    return 0

if __name__=="__main__":
    sys.exit(main())
