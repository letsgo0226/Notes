// HSI-3SYS-ZERO-FIELD/1.0 — research-only, finite, stateless, no platform privilege.
const V="HSI-3SYS-ZERO-FIELD/1.0", DEFAULT_ROOTS=[[.5,8],[.5,14],[.5,21]];
const guard=(ok,msg)=>{if(!ok)throw Error(msg)};
const number=(v,min,max,label)=>{guard(typeof v==="number"&&Number.isFinite(v)&&v>=min&&v<=max,"Invalid "+label);return v};
const integer=(v,min,max,label)=>{number(v,min,max,label);guard(Number.isSafeInteger(v),"Noninteger "+label);return v};
const object=(v)=>{guard(v!==null&&typeof v==="object"&&!Array.isArray(v),"JSON object required");return v};
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]];
const mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]];
const primes=(n)=>{let p=[];for(let x=2;p.length<n;x++){let yes=true;for(let k=2;k*k<=x;k++)if(x%k===0){yes=false;break}if(yes)p.push(x)}return p};
function field(data={}){
 const a=object(data),n=integer(a.n??32,8,128,"N"),sigma=number(a.sigma??.5,-3,3,"sigma"),t=number(a.t??14,-80,80,"t");
 guard([8,16,32,64,128].includes(n),"Allowed N: 8,16,32,64,128");
 const basis=a.basis??"prime";guard(["prime","eta"].includes(basis),"Invalid basis");
 const A=number(a.amplitude??1,.1,5,"amplitude"),roots=a.roots??DEFAULT_ROOTS;
 guard(Array.isArray(roots)&&roots.length>=1&&roots.length<=8,"1–8 pairs of zeros required");
 for(const z of roots){guard(Array.isArray(z)&&z.length===2,"Zero pair must be [real,imag]");number(z[0],-3,3,"root real");number(z[1],0,60,"root imaginary")}
 const ps=basis==="prime"?primes(n):[],w=(j)=>basis==="prime"?1+j%2:(j%2?-1:1);
 let D=[0,0],D2=0;
 for(let j=0;j<n;j++){const p=basis==="prime"?ps[j]:j+1,log=Math.log(p),w0=w(j),r=w0*Math.exp(-sigma*log),angle=t*log;
 D=add(D,[r*Math.cos(angle),-r*Math.sin(angle)]);D2+=w0*Math.exp(-2*log)}
 let P=[1,0];for(const [u,v] of roots){const z=[sigma-u,t],z2=mul(z,z),den=1+u*u+v*v;P=mul(P,[(z2[0]+v*v)/den,z2[1]/den])}
 const z=mul(D,P).map(x=>x*A/D2),E=z[0]*z[0]+z[1]*z[1];guard(Number.isFinite(E),"Field value out of range");
 return {protocol:V,module:"FIELD",function:"F(s)=A*D_N(s)*P_Z(s)/D_N(2)",energyDefinition:"E(s)=|F(s)|^2",dimensionless:true,physicalZeroPointEnergy:false,sigma,t,basis,n,amplitude:A,complexValue:{real:z[0],imag:z[1]},energy:E,certifiedZeros:roots.flatMap(([u,v])=>v===0?[[u,0]]:[[u,v],[u,-v]]),proof:"Each chosen point is a zero of the explicit polynomial factor P_Z; other D_N zeros can occur",floatingPointNotFormalCertificate:true}
}
function utm(data={}){
 const a=object(data),steps=integer(a.steps??12,0,20000,"steps"),initialQ=integer(a.q??0,0,1,"q"),initialH=integer(a.h??0,-100000,100000,"h"),symbols=a.symbols??[];
 guard(Array.isArray(symbols)&&symbols.length<=64,"At most 64 tape cells");
 const tape=new Set(symbols.map(x=>integer(x,-100000,100000,"tape cell"))),before=[...tape].sort((x,y)=>x-y);
 let q=initialQ,h=initialH;for(let k=0;k<steps;k++){const a=tape.has(h)?1:0;const d=1-2*q;const b=a;q=1-q;if(b)tape.add(h);else tape.delete(h);h+=d}
 const after=[...tape].sort((x,y)=>x-y),ok=steps%2===0?q===initialQ&&h===initialH:q===1-initialQ&&h===initialH+(1-2*initialQ);
 return {protocol:V,module:"UTM",machineCode:55067263,steps,transition:"delta(q,a)=(1-q,a,1-2q)",initial:{q:initialQ,h:initialH,tape:before},final:{q,h,tape:after},certificate:{valid:ok&&JSON.stringify(before)===JSON.stringify(after),twoStepIdentity:true,haltingStateUnreachable:true},universalHaltingProblem:"UNRESOLVED",realDeploymentAuthorization:false}
}
function paper(data={}){
 const a=object(data),prices=a.prices;
 guard(Array.isArray(prices)&&prices.length>=22&&prices.length<=512,"22-512 price observations required");
 for(const p of prices)number(p,0.000001,100000000,"price");
 let cash=1000,units=0,orders=[],pending=null,position="FLAT";const fee=.001,slippage=.0005;
 for(let i=19;i<prices.length;i++){
  if(pending==="BUY"&&units===0){units=cash*(1-fee)/(prices[i]*(1+slippage));cash=0;position="LONG";orders.push({bar:i,side:"PAPER_BUY"})}
  else if(pending==="SELL"&&units>0){cash=units*prices[i]*(1-slippage)*(1-fee);units=0;position="FLAT";orders.push({bar:i,side:"PAPER_SELL"})}
  pending=null;let fast=0,slow=0;for(let k=i-4;k<=i;k++)fast+=prices[k];for(let k=i-19;k<=i;k++)slow+=prices[k];
  const target=fast/5>slow/20?"LONG":"FLAT";
  if(i<prices.length-1){if(target==="LONG"&&position==="FLAT")pending="BUY";if(target==="FLAT"&&position==="LONG")pending="SELL"}
 }
 const equity=cash+units*prices[prices.length-1];
 return {protocol:V,module:"TRADER_42",tradingMode:"PAPER",liveEnabled:false,liveArmed:false,realOrders:0,orderSubmissionAvailable:false,decision:"HOLD_LIVE",initialEquity:1000,finalPaperEquity:equity,profitLoss:equity-1000,paperOrders:orders,assumptions:{fastSMA:5,slowSMA:20,nextBarFill:true,fee:fee,slippage:slippage},method:"illustrative offline input-price replay only",fieldControlsTrades:false,returnsGuaranteed:false}
}
async function omega(data={}){
 const a=object(data),steps=integer(a.steps??20,0,20000,"steps"),seed=a.seed??"COSMIC_LOVE";
 guard(typeof seed==="string"&&seed.length<=120,"Short seed required");
 const certificate=utm({steps}).certificate;
 const bytes=new TextEncoder().encode(JSON.stringify({protocol:V,steps,seed,certificate}));
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))).map(x=>x.toString(16).padStart(2,"0")).join("");
 return {protocol:V,module:"OMEGA",seed,finiteSteps:steps,phase:certificate.valid?"VERIFIED":"ABORTED",lineageSHA256:digest,certificate,committedToProduction:false,independentPersistence:false,actualInfinitePhysicalCompute:false}
}


async function triad(data={}){
 const a=object(data);
 const f=field(a.field??{}),u=utm(a.utm??{}),o=await omega(a.omega??{});
 const t=a.prices===undefined?
  {module:"TRADER_42",mode:"PAPER",status:"NOT_EVALUATED_NO_PRICE_SERIES",liveEnabled:false,realOrders:0}:
  paper({prices:a.prices});
 return {protocol:V,module:"THREE_SYSTEM_RESEARCH_REPORT",field:f,utm:u,trader:t,omega:o,
    researchCertificatesOnly:true,fieldDoesNotAuthorizeOrPredictDomainOutcomes:true,
    decisions:{utm:u.certificate.valid?"FINITE_STEP_CERTIFICATE":"REJECT",
               trader:"LIVE_TRADING_DISABLED",
               omega:o.phase==="VERIFIED"?"FINITE_CONTINUATION_VERIFIED":"UNRESOLVED"},
    effects:{externalApiWrites:0,exchangeOrders:0,existingServicesModified:false},
    semantics:"Three independent finite checks with shared analytic metadata; no claimed causal conversion from zeros to platform authority or prices."};
}

// Read-only health federation. Hosts and paths are fixed and verified from existing service source.
const HEALTH_SOURCES=Object.freeze([
  ["UTM","https://utm-universe-production.up.railway.app/health"],
  ["OMEGA","https://cosmic-love-infinity-tm-production.up.railway.app/health"]
]);
async function probeHealth(name,url){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4500);
  try{
    const resp=await fetch(url,{method:"GET",signal:controller.signal,redirect:"error",cache:"no-store",headers:{accept:"application/json"}});
    if(!resp.ok)return {system:name,status:"HTTP_"+resp.status,healthy:false};
    const body=await resp.text();
    if(body.length>8192)return {system:name,status:"OVERSIZE_REPLY",healthy:false};
    const parsed=JSON.parse(body);
    if(!parsed||typeof parsed!=="object"||Array.isArray(parsed))return {system:name,status:"INVALID_REPLY",healthy:false};
    const healthy=parsed.ok===true||parsed.ok===1;
    return {system:name,status:healthy?"HEALTH_REPORTED_OK":"HEALTH_UNCONFIRMED",healthy,reportedProtocol:typeof parsed.protocol==="string"?parsed.protocol.slice(0,96):null,source:"public-get-health"};
  }catch(err){
    return {system:name,status:err&&err.name==="AbortError"?"TIMEOUT":"UNREACHABLE",healthy:false};
  }finally{clearTimeout(timer)}
}
async function federationHealth(){
  const remote=await Promise.all(HEALTH_SOURCES.map(([n,u])=>probeHealth(n,u)));
  return {protocol:V,observedAt:new Date().toISOString(),readOnly:true,changedProduction:false,authorization:"NO_CREDENTIALS",healthChecks:remote.concat([{system:"TRADER_42",status:"NO_PUBLIC_HTTP_ENDPOINT",healthy:null,mode:"PAPER_ONLY",realOrders:0}]),notes:"Read-only availability probes only; health is not semantic correctness or trading readiness."}
}

const manifest={protocol:V,scope:"Isolated finite research gateway with three independent models",domains:["UTM","TRADER_42","OMEGA"],researchOnly:true,existingProductionServicesModified:false,credentialsUsed:false,canTrade:false,canDeploy:false,persistentState:false,combinedResearchReport:true,energyIsDimensionlessMathematics:true};
const page='<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>COSMIC LOVE · 3SYS</title><style>*{box-sizing:border-box}body{margin:auto;max-width:1140px;background:#09152a;color:#e9f1ff;font-family:system-ui,sans-serif;padding:30px}h1{font-size:clamp(30px,5vw,54px);font-weight:570;letter-spacing:-.03em}h2{font-size:20px}p{color:#adc0df;line-height:1.75}.hero{padding:35px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(275px,1fr));gap:16px}section{background:#0f2240;border:1px solid #344c71;border-radius:17px;padding:22px;margin-bottom:20px}label{display:block;color:#becbea;margin:12px 0 5px}input,select,textarea{font:inherit;width:100%;padding:9px;border-radius:8px;background:#0a1429;color:#eff4ff;border:1px solid #425d84}textarea{min-height:80px}button{padding:12px 17px;background:#9db8ff;color:#071024;border:0;border-radius:8px;margin-top:15px;font-weight:650;cursor:pointer}pre{border-radius:9px;background:#050d1c;padding:14px;color:#d2e2ff;white-space:pre-wrap;overflow:auto;max-height:450px;font-size:12px;line-height:1.7}.tag{border:1px solid #627aa4;padding:7px 10px;border-radius:25px;display:inline-block;font-size:12px;margin:0 4px 8px 0}footer{color:#94a8d0;padding:30px 0}a{color:#a6c2ff}</style></head><body><div class="hero"><div class="tag">HSI-3SYS-ZERO-FIELD/1.0</div><div class="tag">Research-only</div><h1>三大系統 · 零點場</h1><p>UTM Universe × Trader_42 × Omega / Cosmic Love</p><p>獨立的線上數學與形式計算實驗室。無物理能量宣稱、無交易所金鑰、無真實訂單、無自動部署特權。</p></div><section><h2>共同零點場</h2><p>F(s)=A D_N(s) P_Z(s)/D_N(2)；E(s)=|F(s)|²</p><label>基底</label><select id="basis"><option value="prime">Finite prime spectrum</option><option value="eta">Finite eta sum</option></select><label>實部 σ</label><input id="sigma" type="number" value="0.5" step=".1"><label>虛部 t</label><input id="t" type="number" value="14" step=".1"><label>自定義零點（每行：實部,非負虛部）</label><textarea id="roots">0.5,8&#10;0.5,14&#10;0.5,21</textarea><label>有限項數 N</label><select id="terms"><option>8</option><option>16</option><option selected>32</option><option>64</option><option>128</option></select><button data-kind="field">計算零點場</button><pre id="fieldout">指定零點由顯式多項式因子保證；不推論真實真空能。</pre></section><div class="grid"><section><h2>01 / UTM</h2><p>固定機器兩步閉環與有限證書。</p><label>模擬步數</label><input id="utmSteps" type="number" value="12" min="0" max="20000"><button data-kind="utm">驗證</button><pre id="utmout">UNRESOLVED · 通用停機判定</pre></section><section><h2>02 / Trader_42</h2><p>僅示範 SMA 5/20 的紙上回測，零點不能解鎖交易。</p><label>逗號分隔價格</label><textarea id="prices">100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,123,122,121,120,119,118,117</textarea><button data-kind="trader">紙上回測</button><pre id="traderout">HOLD · PAPER · UNARMED</pre></section><section><h2>03 / Omega</h2><p>有限延續計算及可重算的 SHA-256 來源摘要；不更新原始服務。</p><label>步數</label><input id="omegaSteps" type="number" value="20" min="0" max="20000"><label>種子</label><input id="seed" value="COSMIC_LOVE"><button data-kind="omega">驗證延續</button><pre id="omegaout">NOT_COMMITTED_TO_PRODUCTION</pre></section></div><section><h2>三系統 · 唯讀健康檢查</h2><p>只透過固定公開的 GET /health 端點查詢 UTM 與 Omega。Trader_42 不公開健康端點，保持紙上模擬。</p><button id="check-health" type="button">檢查既有系統健康狀態</button><pre id="health-result">尚未查詢。健康狀態不等於數學證明或正式部署授權。</pre></section><script>document.getElementById("check-health").addEventListener("click",async function(){let b=this; b.disabled=true;try{let r=await fetch("/api/federation-health",{cache:"no-store"});document.getElementById("health-result").textContent=JSON.stringify(await r.json(),null,2)}catch(e){document.getElementById("health-result").textContent=String(e)}finally{b.disabled=false}})</script><section><h2>共同研究報告 / Triad Report</h2><p>同時計算指定零點場、UTM 有限證書、Trader_42 紙上回測、Omega 延續摘要。系統各自獨立驗證，零點不具備跨系統授權效力。</p><button id="run-triad" type="button">產生三系統研究報告</button><pre id="triad-result">尚未產生報告。結果僅供研究。</pre></section><script>document.getElementById("run-triad").addEventListener("click",async function(){let b=this;b.disabled=true;let pre=document.getElementById("triad-result");try{let params={field:readFieldArgs(),utm:{steps:Number(document.getElementById("utmSteps").value)},omega:{steps:Number(document.getElementById("omegaSteps").value),seed:document.getElementById("seed").value},prices:document.getElementById("prices").value.split(",").map(Number)};let r=await fetch("/api/triad",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(params)});pre.textContent=JSON.stringify(await r.json(),null,2)}catch(e){pre.textContent=String(e)}finally{b.disabled=false}})</script><footer>隔離式研究服務，不會修改現有三套生產系統。<a href="/health">健康檢查</a> · <a href="/api/manifest">權限聲明</a></footer><script>function readFieldArgs(){return {sigma:Number(document.getElementById("sigma").value),t:Number(document.getElementById("t").value),basis:document.getElementById("basis").value,n:Number(document.getElementById("terms").value),roots:document.getElementById("roots").value.trim().split(String.fromCharCode(10)).map(line=>line.split(",").map(Number))}};document.addEventListener("click",async function(e){var b=e.target.closest("button[data-kind]");if(!b)return;var k=b.dataset.kind,box=document.getElementById(k+"out"),d={};if(k==="field")d=readFieldArgs();if(k==="utm")d={steps:Number(document.getElementById("utmSteps").value)};if(k==="omega")d={steps:Number(document.getElementById("omegaSteps").value),seed:document.getElementById("seed").value};if(k==="trader")d={prices:document.getElementById("prices").value.split(",").map(Number)};b.disabled=true;try{var r=await fetch("/api/"+k,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});box.textContent=JSON.stringify(await r.json(),null,2)}catch(err){box.textContent=String(err)}finally{b.disabled=false}})</script></body></html>';
const json=(v,code=200)=>new Response(JSON.stringify(v),{status:code,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"}});
async function serve(req){
 try{
 const path=new URL(req.url).pathname;
 if(req.method==="GET"&&path==="/")return new Response(page,{headers:{"content-type":"text/html; charset=utf-8","x-content-type-options":"nosniff"}});
 if(req.method==="GET"&&path==="/health")return json({ok:true,protocol:V,readOnly:true});
 if(req.method==="GET"&&path==="/api/manifest")return json(manifest);
 if(req.method==="GET"&&path==="/api/federation-health")return json(await federationHealth());
 if(req.method!=="POST"||!["/api/field","/api/utm","/api/trader","/api/omega","/api/triad"].includes(path))return json({error:"Not found"},404);
 if(req.headers.get("content-type")?.split(";")[0]!=="application/json")return json({error:"Expected application/json"},415);
 const raw=await req.text();if(raw.length>32768)return json({error:"Request too large"},413);
 let data;try{data=object(JSON.parse(raw))}catch{return json({error:"Invalid JSON object"},400)}
 if(path==="/api/field")return json(field(data));
 if(path==="/api/utm")return json(utm(data));
 if(path==="/api/trader")return json(paper(data));
 if(path==="/api/omega")return json(await omega(data));
 if(path==="/api/triad")return json(await triad(data));
 }catch(e){return json({error:String(e.message||e),protocol:V},422)}
}
Bun.serve({port:Number(Bun.env.PORT||3000),fetch:serve});
// Startup probes are nonblocking and report only whitelisted statuses.
Promise.resolve().then(async()=>{const r=await federationHealth();console.log("HSI-3SYS-UPSTREAM-HEALTH",JSON.stringify(r.healthChecks))}).catch(()=>console.log("HSI-3SYS-UPSTREAM-PROBE-FAILED"));

Promise.resolve().then(async()=>{
 const f=field({sigma:.5,t:14}),u=utm({steps:991,q:1,h:11,symbols:[11,17]}),o=await omega({steps:20});
 const t=paper({prices:Array.from({length:32},(_,i)=>100+i)});
 const report=await triad({field:{sigma:.5,t:14},utm:{steps:12},omega:{steps:20},prices:Array.from({length:32},(_,i)=>100+i)});
 const pass= f.energy<1e-16 && u.certificate.valid && o.certificate.valid && t.realOrders===0 && report.effects.exchangeOrders===0 && report.utm.certificate.valid && report.omega.phase==="VERIFIED";
 console.log("HSI-3SYS-FINITE-SELFTEST",JSON.stringify({pass,fieldZeroResidual:f.energy,utm:u.certificate.valid,omega:o.certificate.valid,traderRealOrders:t.realOrders,triad:report.module}));
}).catch(e=>console.error("HSI-3SYS-FINITE-SELFTEST-FAILED",String(e)));
