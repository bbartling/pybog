
import React, { useLayoutEffect, useRef, useState } from "react";

// --- Tokens
const TOKENS = {
  bg: "#F7F8FA",
  grid: "#E9EBF2",
  border: "#3F3F4B",
  text: "#1F1F1F",
  muted: "#6D6E7A",
  nodeHeader: "#C9C7DF",
  nodeFooter: "#F6F2C7",
  ok: "#2DB72D",
  chip: "#ECEEF5",
  port: "#59586A",
};

// Edge animations
const STYLES = `
@keyframes dash { to { stroke-dashoffset: -1000; } }
.poly-run { stroke-dasharray: 8 6; animation: dash 2.5s linear infinite; }
.poly-await { stroke-dasharray: 2 8; }
.poly-change { stroke-dasharray: 10 6; }
`;

// Helpers & types
const uid = () => Math.random().toString(36).slice(2, 10);
type Role = "user" | "system" | "process";
type Status = "running" | "awaiting_approval" | "approved" | "changes_requested";
type Message = { id: string; role: Role; text: string; time: string; status?: Status; blocks?: string[] };
type Session = { id: string; name: string };

// Icons
const Icon = {
  Dot: ({ color="#000" }: any) => <span style={{width:10,height:10,borderRadius:999,background:color,display:"inline-block"}}/>,
  Gear: () => <span style={{fontWeight:700}}>⚙️</span>,
  User: () => <span style={{fontWeight:700}}>👤</span>,
  Term: () => <span style={{fontWeight:700}}>▣</span>,
  Caret: ({open}:{open:boolean}) => <span>{open ? "▾" : "▸"}</span>,
  Pencil: () => <span>✎</span>,
  Trash: () => <span>🗑️</span>,
};

// Mock n8n
function useMockN8N(log:(s:string)=>void){
  async function analyze(text:string):Promise<Message>{
    log(`POST /n8n/analysis-chat → "${text.slice(0,32)}..."`);
    await new Promise(r=>setTimeout(r,600));
    return { id:uid(), role:"process", text:"Analyzing your request…", time:new Date().toLocaleTimeString(), status:"running" };
  }
  async function finalizeApproval(k:"approved"|"changes_requested"){
    await new Promise(r=>setTimeout(r,250));
    return k;
  }
  return { analyze, finalizeApproval };
}

// Role style
const ROLE_STYLE: Record<Role,{header:string; body:string; icon:JSX.Element; dash?:boolean}> = {
  user:    { header:"#C9C7DF", body:"#DBDAF5", icon:<Icon.User/> },
  system:  { header:"#D0D6D7", body:"#D4F5E5", icon:<Icon.Term/> },
  process: { header:"#BFE4FB", body:"#E6F3FE", icon:<Icon.Gear/>, dash:true },
};

// Bubble
function Bubble({msg,refCb,onApprove,onChanges}:{msg:Message; refCb:(el:HTMLDivElement|null)=>void; onApprove?:()=>void; onChanges?:()=>void}){
  const style = ROLE_STYLE[msg.role];
  const isUser = msg.role==="user";
  return (
    <div style={{width:440, display:"flex", justifyContent:isUser?"flex-start":"flex-end"}}>
      <div ref={refCb} style={{width:"100%"}}>
        <div style={{border:`2px ${style.dash?'dashed':'solid'} ${TOKENS.border}`, borderRadius:12, overflow:"hidden", background:"#fff"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"6px 10px", background:style.header}}>
            <div style={{display:"flex",gap:8,alignItems:"center",fontWeight:600}}>{style.icon}{String(msg.role).toUpperCase()}</div>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              <Icon.Dot color={isUser?TOKENS.muted:(msg.status==="approved"?TOKENS.ok:TOKENS.muted)} />
              {msg.status==="running" && <span style={{border:`2px solid ${TOKENS.border}`,borderRadius:999, padding:"2px 8px", background:TOKENS.chip}}>Running…</span>}
              {msg.status==="awaiting_approval" && <span style={{border:`2px solid ${TOKENS.border}`,borderRadius:999, padding:"2px 8px", background:TOKENS.nodeFooter}}>Awaiting approval</span>}
              {msg.status==="changes_requested" && <span style={{border:`2px solid ${TOKENS.border}`,borderRadius:999, padding:"2px 8px", background:"#FFF0CC"}}>Changes requested</span>}
              {msg.status==="approved" && <span style={{border:`2px solid ${TOKENS.border}`,borderRadius:999, padding:"2px 8px", background:"#D6F3D7"}}>Approved</span>}
            </div>
          </div>
          <div style={{padding:"10px 12px", background:style.body}}>
            <div style={{fontSize:14, lineHeight:"20px"}}>{msg.text}</div>
            {msg.blocks && !!msg.blocks.length && (
              <div style={{marginTop:8, fontSize:12}}>
                <div style={{fontWeight:600, marginBottom:4}}>Proposed Blocks</div>
                <ul style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:4}}>
                  {msg.blocks.map(b=>(
                    <li key={b} style={{display:"flex",gap:8,alignItems:"center",border:`2px solid ${TOKENS.border}`,borderRadius:6,padding:"4px 8px",background:"#ffffffcc"}}>
                      <Icon.Dot color={TOKENS.port}/> {b}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div style={{padding:"6px 10px", fontSize:12, background:TOKENS.nodeFooter, color:TOKENS.muted}}>{msg.time}</div>
        </div>
        {msg.status==="awaiting_approval" && msg.role!=="user" && (
          <div style={{display:"flex",gap:8, marginTop:8}}>
            <button onClick={onApprove} style={{border:`2px solid ${TOKENS.border}`, borderRadius:8, padding:"4px 12px"}}>Approve ✓</button>
            <button onClick={onChanges} style={{border:`2px solid ${TOKENS.border}`, borderRadius:8, padding:"4px 12px"}}>Request Changes ✎</button>
          </div>
        )}
      </div>
    </div>
  );
}

// Edge logic
function computeEdgePoints(
  a:{left:number;right:number;top:number;height:number},
  b:{left:number;right:number;top:number;height:number},
  aLeft:boolean, bLeft:boolean,
  canvas:{left:number;top:number}
):Array<[number,number]>{
  const x1=(aLeft?a.right:a.left)-canvas.left;
  const y1=a.top+a.height/2-canvas.top;
  const x2=(bLeft?b.right:b.left)-canvas.left;
  const y2=b.top+b.height/2-canvas.top;
  if(Math.abs(y2-y1)<40) return [[x1,y1],[x2,y2]];
  const mid=x1+40; return [[x1,y1],[mid,y1],[mid,y2],[x2,y2]];
}

// Hook to compute edges
function useEdges(msgs:Message[], refs:React.MutableRefObject<Record<string,HTMLDivElement|null>>, canvasRef:React.RefObject<HTMLDivElement>){
  const [edges,setEdges]=useState<Array<{pts:Array<[number,number]>; cls:string}>>([]);
  useLayoutEffect(()=>{
    const cv=canvasRef.current; if(!cv) return;
    const cr=cv.getBoundingClientRect();
    const out:any[]=[];
    for(let i=0;i<msgs.length-1;i++){
      const a=refs.current[msgs[i].id]; const b=refs.current[msgs[i+1].id];
      if(!a||!b) continue;
      const ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect();
      const pts=computeEdgePoints(
        {left:ra.left,right:ra.right,top:ra.top,height:ra.height},
        {left:rb.left,right:rb.right,top:rb.top,height:rb.height},
        msgs[i].role==="user",
        msgs[i+1].role==="user",
        {left:cr.left,top:cr.top}
      );
      const st=msgs[i+1].status; 
      const cls= st==="running"?"poly-run": st==="awaiting_approval"?"poly-await": st==="changes_requested"?"poly-change":"poly-approved";
      out.push({pts,cls});
    }
    setEdges(out);
  },[msgs,refs,canvasRef]);
  return edges;
}

// Top bar and Sidebar
function TopBar({onSeed}:{onSeed:()=>void}){
  return (
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",border:`2px solid ${TOKENS.border}`,borderRadius:12,padding:"8px 12px",background:"#fff"}}>
      <div style={{fontWeight:600}}>N4 Builder — <span style={{opacity:.7}}>POWERED BY PYBOG</span></div>
      <div style={{display:"flex",gap:8,alignItems:"center"}}>
        <div style={{display:"flex",gap:8,alignItems:"center",border:`2px solid ${TOKENS.border}`,borderRadius:999,padding:"4px 10px",background:TOKENS.chip}}>
          <span style={{width:10,height:10,borderRadius:999,background:TOKENS.ok,display:"inline-block"}}/> Healthy
        </div>
        <button onClick={onSeed} style={{border:`2px solid ${TOKENS.border}`,borderRadius:8,padding:"4px 8px"}}>▶ Demo Flow</button>
      </div>
    </div>
  );
}

function Sidebar({sessions,collapsed,setCollapsed,onRename,onDelete,onAdd}:{sessions:Session[];collapsed:boolean;setCollapsed:(b:boolean)=>void;onRename:(id:string)=>void;onDelete:(id:string)=>void;onAdd:()=>void}){
  return (
    <aside style={{border:`2px solid ${TOKENS.border}`,borderRadius:12,background:"#fff"}}>
      <div style={{borderBottom:`2px solid ${TOKENS.border}`,padding:"8px 12px",display:"flex",justifyContent:"space-between",alignItems:"center",fontWeight:600,background:TOKENS.chip}}>PROJECT NAVIGATOR <button onClick={onAdd} style={{border:`2px solid ${TOKENS.border}`,borderRadius:6,padding:"2px 6px"}}>+ New</button></div>
      <div style={{padding:8}}>
        <button onClick={()=>setCollapsed(!collapsed)} style={{width:"100%",textAlign:"left",display:"flex",gap:8,alignItems:"center",border:`2px solid ${TOKENS.border}`,borderRadius:10,padding:"6px 8px",marginBottom:8}}>
          <Icon.Caret open={!collapsed}/> <span style={{fontWeight:600}}>CHAT SESSIONS ({sessions.length})</span>
        </button>
        {!collapsed && sessions.map(s=>(
          <div key={s.id} style={{display:"flex",justifyContent:"space-between",alignItems:"center",border:`2px solid ${TOKENS.border}`,borderRadius:8,padding:"6px 8px",marginBottom:8}}>
            <div style={{display:"flex",gap:8,alignItems:"center"}}><span style={{width:8,height:8,borderRadius:999,background:TOKENS.muted,display:"inline-block"}}/> {s.name}</div>
            <div style={{display:"flex",gap:6}}>
              <button onClick={()=>onRename(s.id)} style={{border:`2px solid ${TOKENS.border}`,borderRadius:6,padding:"2px 6px"}}><Icon.Pencil/></button>
              <button onClick={()=>onDelete(s.id)} style={{border:`2px solid ${TOKENS.border}`,borderRadius:6,padding:"2px 6px"}}><Icon.Trash/></button>
            </div>
          </div>
        ))}
        {!collapsed && <div style={{border:`2px solid ${TOKENS.border}`,borderRadius:8,padding:"10px 12px",opacity:.7}}>No files in this session</div>}
      </div>
    </aside>
  );
}

// Main App
export default function App(){
  const [messages,setMessages]=useState<Message[]>([
    {id:uid(),role:"system",text:"PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.",time:new Date().toLocaleTimeString()}
  ]);
  const [text,setText]=useState("");
  const [sessions,setSessions]=useState<Session[]>([{id:uid(),name:"Session 3"},{id:uid(),name:"Session 2"},{id:uid(),name:"Session 1"}]);
  const [collapsed,setCollapsed]=useState(false);

  const {analyze,finalizeApproval}=useMockN8N(()=>{});

  const refs=useRef<Record<string,HTMLDivElement|null>>({});
  const canvasRef=useRef<HTMLDivElement|null>(null);
  const edges=useEdges(messages,refs,canvasRef);

  async function send(){
    const content=text.trim(); if(!content) return; setText("");
    const userMsg:Message={id:uid(),role:"user",text:content,time:new Date().toLocaleTimeString()};
    setMessages(m=>[...m,userMsg]);
    const running=await analyze(content);
    setMessages(m=>[...m,running]);
    setTimeout(()=>{
      setMessages(m=>m.map(x=>x.id===running.id?{...x,role:"system",status:"awaiting_approval",text:"Draft generated. Review proposed blocks and approve to build in Workbench.",blocks:["SystemMode (Enum Writable)","OccProgram (Folder)","Economizer (Folder)","Thermostat (Folder)","Stages (Folder)","Conditions (Folder)"]}:x));
    },800);
  }
  async function approveDraft(id:string){
    const res=await finalizeApproval("approved");
    setMessages(m=>m.map(x=>x.id===id?{...x,status:res,text:"Approved. PyBOG will compile Niagara wire‑sheet blocks and bindings."}:x));
  }
  async function requestChanges(id:string){
    const res=await finalizeApproval("changes_requested");
    setMessages(m=>m.map(x=>x.id===id?{...x,status:res,text:"Requested changes recorded. Please specify adjustments (e.g., different setpoints, occupancy logic)."}:x));
  }
  function seed(){
    const now=()=>new Date().toLocaleTimeString();
    setMessages([
      {id:uid(),role:"system",text:"PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.",time:now()},
      {id:uid(),role:"user",text:"Design AHU-1 with 2-stage cooling, 1-stage heating, economizer.",time:now()},
      {id:uid(),role:"process",text:"Analyzing your request…",time:now(),status:"running"},
      {id:uid(),role:"user",text:"Use occupied/unoccupied via schedule; add free-cooling when OA<55°F.",time:now()},
      {id:uid(),role:"system",text:"Draft generated. Review proposed blocks and approve to build in Workbench.",time:now(),status:"awaiting_approval",blocks:["SystemMode (Enum Writable)","OccProgram (Folder)","Economizer (Folder)","Thermostat (Folder)","Stages (Folder)","Conditions (Folder)"]},
      {id:uid(),role:"user",text:"Looks good—raise Econ enable to 58°F and min position 20%.",time:now()},
      {id:uid(),role:"process",text:"Recomputing with requested changes…",time:now(),status:"running"},
      {id:uid(),role:"system",text:"Requested changes recorded. Please specify adjustments (e.g., different setpoints, occupancy logic).",time:now(),status:"changes_requested"},
      {id:uid(),role:"user",text:"Confirmed. Proceed.",time:now()},
      {id:uid(),role:"system",text:"Approved. PyBOG will compile Niagara wire‑sheet blocks and bindings.",time:now(),status:"approved"},
    ]);
  }

  function rename(id:string){ const s=sessions.find(x=>x.id==id); if(!s) return; const name=prompt("Rename session",s.name); if(!name) return; setSessions(list=>list.map(x=>x.id==id?{...x,name}:x)); }
  function del(id:string){ if(!confirm("Delete this chat session?")) return; setSessions(list=>list.filter(x=>x.id!=id)); }
  function add(){ const name=prompt("New session name",`Session ${sessions.length+1}`)||`Session ${sessions.length+1}`; setSessions(list=>[{id:uid(),name},...list]); }

  return (
    <div style={{height:"100%",width:"100%",background:TOKENS.bg}}>
      <div style={{margin:"8px"}}><TopBar onSeed={seed}/></div>

      <div style={{display:"grid",gridTemplateColumns:"minmax(260px,320px) 1fr",gap:12,padding:8,height:"calc(100vh - 72px)"}}>
        <div><Sidebar sessions={sessions} collapsed={collapsed} setCollapsed={setCollapsed} onRename={rename} onDelete={del} onAdd={add}/></div>

        <div style={{display:"flex",flexDirection:"column"}}>
          <div ref={canvasRef} style={{position:"relative",flex:1,border:`2px solid ${TOKENS.border}`,borderRadius:12,overflow:"hidden"}}>
            <div style={{position:"absolute",inset:0,backgroundImage:`linear-gradient(0deg, ${TOKENS.grid} 1px, transparent 1px), linear-gradient(90deg, ${TOKENS.grid} 1px, transparent 1px)`,backgroundSize:"16px 16px",backgroundPosition:"center"}}/>
            <svg style={{position:"absolute",inset:0,pointerEvents:"none"}} width="100%" height="100%">
              <defs><style>{STYLES}</style></defs>
              {edges.map((e,i)=>(
                e.pts.length===2
                ? <line key={i} x1={e.pts[0][0]} y1={e.pts[0][1]} x2={e.pts[1][0]} y2={e.pts[1][1]} stroke={TOKENS.border} strokeWidth={2} className={e.cls}/>
                : <polyline key={i} points={e.pts.map(p=>p.join(",")).join(" ")} fill="none" stroke={TOKENS.border} strokeWidth={2} className={e.cls}/>
              ))}
            </svg>
            <div style={{position:"relative",height:"100%",width:"100%",padding:24}}>
              <div style={{display:"flex",flexWrap:"wrap",gap:40,alignItems:"flex-start"}}>
                {messages.map(m=>(
                  <Bubble key={m.id} msg={m} refCb={(el)=>refs.current[m.id]=el} onApprove={m.status==="awaiting_approval"?()=>approveDraft(m.id):undefined} onChanges={m.status==="awaiting_approval"?()=>requestChanges(m.id):undefined}/>
                ))}
              </div>
            </div>
            <div style={{position:"absolute",left:12,bottom:110,display:"flex",flexDirection:"column",gap:8}}>
              {["+", "–", "□"].map(k=>(<button key={k} style={{width:40,height:36,border:`2px solid ${TOKENS.border}`,borderRadius:10,background:"#fff"}}>{k}</button>))}
            </div>
            <div style={{position:"absolute",right:12,bottom:110,border:`2px solid ${TOKENS.border}`,borderRadius:10,background:TOKENS.chip,width:240,height:140}}/>
            <div style={{position:"absolute",left:0,right:0,bottom:0,padding:12}}>
              <div style={{display:"flex",gap:8,alignItems:"center",border:`2px solid ${TOKENS.border}`,borderRadius:12,background:"#fff",padding:"8px 12px"}}>
                <button style={{border:`2px solid ${TOKENS.border}`,borderRadius:8,padding:"4px 12px"}}>Upload</button>
                <input value={text} onChange={e=>setText((e.target as HTMLInputElement).value)} onKeyDown={e=>{if(e.key==="Enter") send();}} placeholder="Describe your HVAC control requirements or drop sequence PDFs…" style={{flex:1,outline:"none"}}/>
                <button onClick={send} style={{border:`2px solid ${TOKENS.border}`,borderRadius:8,padding:"4px 12px"}}>Send ➤</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
