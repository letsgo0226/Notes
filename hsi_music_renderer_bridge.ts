import { fal } from "@fal-ai/client";

const json=(x:any,status=200)=>new Response(JSON.stringify(x),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});
const model=()=>Bun.env.HSI_MUREKA_MODEL||"mureka-9.5";
const configured=()=>Boolean(Bun.env.FAL_KEY&&Bun.env.HSI_BRIDGE_TOKEN);
const cleanErr=(e:any)=>({
  name:String(e?.name||"Error").slice(0,120),
  message:String(e?.message||e).slice(0,1200),
  status:e?.status??e?.statusCode??e?.response?.status??null
});
function bearer(req:Request){const h=req.headers.get("authorization")||"";return h.startsWith("Bearer ")?h.slice(7):""}
async function fail(stage:string,e:any){
  const d=cleanErr(e);
  console.error(JSON.stringify({event:"renderer_error",stage,...d}));
  return json({error:"renderer_error",stage,...d},502);
}

Bun.serve({
  port:Number(Bun.env.PORT||3000),
  async fetch(req){
    const u=new URL(req.url);
    if(u.pathname==="/health") return json({ok:true,protocol:"HSI-MUSIC-RENDER-BRIDGE/1.1",provider:"fal-mureka",configured:configured(),model:model(),route:"lyrics-then-song",accepts:"HSI-MUSIC-2K/1"});
    if(u.pathname!=="/render"||req.method!=="POST") return json({error:"not_found"},404);
    if(!configured()) return json({error:"renderer_not_configured",need:["FAL_KEY","HSI_BRIDGE_TOKEN"]},503);
    if(bearer(req)!==Bun.env.HSI_BRIDGE_TOKEN) return json({error:"unauthorized"},401);
    let q:any;
    try{q=await req.json()}catch{return json({error:"invalid_json"},400)}
    if(q?.p!=="HSI-MUSIC-2K/1"||typeof q?.q!=="string"||!q.q.trim()) return json({error:"invalid_hsi_request"},400);
    const keywords=q.q.trim().slice(0,1200);
    const style=typeof q.s==="string"?q.s.trim().slice(0,1200):"";
    fal.config({credentials:Bun.env.FAL_KEY!});
    let lr:any;
    try{
      lr=await fal.subscribe("mureka/api/generate/lyrics",{input:{prompt:`Write fully original song lyrics from these keywords/concepts: ${keywords}. Use the language implied by the keywords. Give the song a coherent Verse / Chorus / Verse / Bridge / Final Chorus structure. Do not imitate or quote any existing song.`},logs:false});
    }catch(e:any){return fail("lyrics",e)}
    const title=String(lr?.data?.title||"").trim();
    const lyrics=String(lr?.data?.lyrics||"").trim();
    if(!lyrics) return json({error:"lyrics_generation_failed",stage:"lyrics",task_id:lr?.requestId||null},502);
    const musicPrompt=style||`Create an original polished full song matching these concepts: ${keywords}. Natural expressive singing, clear diction, coherent arrangement, memorable chorus, no imitation of any real singer.`;
    let sr:any;
    try{
      sr=await fal.subscribe("mureka/api/generate/song",{input:{model:model(),lyrics,prompt:musicPrompt},logs:false});
    }catch(e:any){return fail("song",e)}
    const d:any=sr?.data||{};
    const url=String(d?.audio?.url||"");
    if(!url) return json({error:"song_generation_failed",stage:"song",task_id:sr?.requestId||null},502);
    return json({status:"SUCCEEDED",url,task_id:sr.requestId||d.song_id||"",renderer:`fal-mureka:${model()}`,render_route:"auto-lyrics-conditioned-song",conditioning:["keywords","generated_lyrics","style"],guide_midi_used:false,lyrics,title,duration_ms:d.duration??null,song_id:d.song_id??null});
  }
});