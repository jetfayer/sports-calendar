const state={
  data:[],meta:{},search:"",sport:"",group:"",region:"",league:"",stage:"",reason:"",minScore:0,
  drcOnly:false,topOnly:false,mode:"watchplus",from:null,to:null
};

const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
function esc(v=""){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function parseDate(v){if(!v)return null;const d=new Date(v);return Number.isNaN(d.getTime())?null:d}
function startOfDay(v){return v?new Date(`${v}T00:00:00`):null}
function endOfDay(v){return v?new Date(`${v}T23:59:59.999`):null}
function addDays(d,n){const x=new Date(d);x.setDate(x.getDate()+n);return x}
function dateInputValue(d){return d.toLocaleDateString("en-CA")}
function fmtDay(d){return new Intl.DateTimeFormat("uk-UA",{weekday:"long",day:"2-digit",month:"long",year:"numeric"}).format(d)}
function fmtTime(d){return new Intl.DateTimeFormat("uk-UA",{hour:"2-digit",minute:"2-digit"}).format(d)}
function fmtShort(d){return new Intl.DateTimeFormat("uk-UA",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(d)}
function uniq(a){return [...new Set(a.filter(Boolean))]}
function optionHtml(values,label){return `<option value="">${label}</option>`+values.sort((a,b)=>a.localeCompare(b)).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}

function setRange(days){
  const today=new Date();today.setHours(0,0,0,0);
  state.from=today;state.to=addDays(today,days);
  $("#dateFrom").value=dateInputValue(state.from);$("#dateTo").value=dateInputValue(state.to);
  $$("[data-days]").forEach(b=>b.classList.toggle("active",Number(b.dataset.days)===days));
  render();
}

function inBaseFilters(e){
  const q=state.search.trim().toLowerCase();
  if(state.sport&&e.sport!==state.sport)return false;
  if(state.group&&e.competition_group!==state.group)return false;
  if(state.region&&e.region!==state.region)return false;
  if(state.league&&e.league!==state.league)return false;
  if(state.stage&&e.stage!==state.stage)return false;
  if(state.reason&&!(e.priority_tags||[]).includes(state.reason))return false;
  if(Number(e.importance||0)<Number(state.minScore||0))return false;
  if(state.drcOnly&&!e.drc_focus)return false;
  if(state.topOnly&&!e.has_top_participant)return false;
  if(q){
    const hay=[
      e.name,e.league,e.sport,e.home,e.away,e.venue,e.region,e.competition_group,e.stage,
      ...(e.priority_tags||[]),...(e.importance_reasons||[])
    ].join(" ").toLowerCase();
    if(!hay.includes(q))return false;
  }
  return true;
}

function dateRows(){
  return state.data.map(e=>({...e,_date:parseDate(e.timestamp)}))
    .filter(e=>e._date)
    .filter(e=>!state.from||e._date>=state.from)
    .filter(e=>!state.to||e._date<=state.to);
}
function baseRows(){return dateRows().filter(inBaseFilters).sort((a,b)=>a._date-b._date||(b.importance||0)-(a.importance||0))}
function filteredRows(){
  return baseRows().filter(e=>
    state.mode==="all" ||
    state.mode==="watchplus" && ["watch","interesting","hot"].includes(e.importance_level) ||
    state.mode==="interesting" && ["interesting","hot"].includes(e.importance_level) ||
    state.mode==="hot" && e.importance_level==="hot"
  );
}

function eventCard(e){
  const lvl=e.importance_level||"normal";
  const badge=lvl==="hot"?"🔥 HOT":lvl==="interesting"?"⭐ Interesting":lvl==="watch"?"👀 Watch":"";
  const reasons=(e.importance_reasons||[]).slice(0,4).join(" · ");
  return `<article class="card ${lvl} ${e.drc_focus?"drc":""}">
    <div><div class="time">${esc(fmtTime(e._date))}</div><div class="sport">${esc(e.sport||"")}</div></div>
    <div>
      <div class="league">${esc(e.league||"")}</div>
      <div class="event">${esc(e.name||[e.home,e.away].filter(Boolean).join(" vs "))}</div>
      ${e.venue?`<div class="venue">${esc(e.venue)}</div>`:""}
      <div class="meta">
        ${e.competition_group?`<span class="tag">${esc(e.competition_group)}</span>`:""}
        ${e.stage&&e.stage!=="Regular"?`<span class="tag">${esc(e.stage)}</span>`:""}
        ${e.region?`<span class="tag">${esc(e.region)}</span>`:""}
        ${e.drc_focus?`<span class="tag drc">🇨🇩 DRC</span>`:""}
      </div>
      ${String(e.postponed).toLowerCase()==="yes"?`<div class="postponed">Postponed</div>`:""}
      ${reasons?`<div class="reasons">${esc(reasons)}</div>`:""}
    </div>
    <div class="badges">
      ${badge?`<span class="priority ${lvl}">${badge}</span>`:""}
      <span class="score">${Number(e.importance||0)} pts</span>
    </div>
  </article>`;
}

function renderDrc(){
  const rows=dateRows().filter(e=>e.drc_focus).sort((a,b)=>a._date-b._date||(b.importance||0)-(a.importance||0));
  $("#summaryDrcCount").textContent=rows.length;$("#drcCount").textContent=rows.length;$("#drcSection").hidden=rows.length===0;
  $("#drcGrid").innerHTML=rows.slice(0,9).map(e=>`<article class="focus-card">
    <div class="focus-date">${esc(fmtShort(e._date))} · ${esc(e.sport||"")}</div>
    <div class="focus-name">${esc(e.name||"")}</div>
    <div class="focus-league">${esc(e.league||"")}${e.stage&&e.stage!=="Regular"?` · ${esc(e.stage)}`:""}</div>
  </article>`).join("");
}

function renderHealth(){
  const stats=state.meta.source_stats||[];
  const counts={OK:0,"NO UPCOMING":0,ERROR:0,UNRESOLVED:0};
  stats.forEach(s=>counts[s.status]=(counts[s.status]||0)+1);
  $("#healthSummary").textContent=`· ${counts.OK||0} OK · ${counts["NO UPCOMING"]||0} no upcoming · ${(counts.ERROR||0)+(counts.UNRESOLVED||0)} issues`;
  $("#healthRows").innerHTML=stats.map(s=>{
    const cls=`status-${String(s.status||"").toLowerCase().replaceAll(" ","-")}`;
    return `<tr>
      <td>${esc(s.name)}</td><td>${esc(s.competition_group||s.kind||"")}</td><td>${esc(s.region||"")}</td>
      <td>${esc(s.resolved_name||s.resolved_id||"—")}</td><td>${esc((s.seasons_tried||[]).join(", ")||"—")}</td>
      <td>${Number(s.received||0)}</td><td>${Number(s.upcoming||0)}</td>
      <td class="${cls}" title="${esc(s.error||"")}">${esc(s.status||"")}</td>
    </tr>`;
  }).join("");
}

function render(){
  const base=baseRows(),rows=filteredRows();
  $("#eventCount").textContent=base.length;
  $("#watchCount").textContent=base.filter(x=>x.importance_level==="watch").length;
  $("#interestingCount").textContent=base.filter(x=>x.importance_level==="interesting").length;
  $("#hotCount").textContent=base.filter(x=>x.importance_level==="hot").length;
  $("#empty").hidden=rows.length!==0;
  renderDrc();

  const groups=new Map();
  for(const e of rows){
    const key=e._date.toLocaleDateString("en-CA");
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(e);
  }
  $("#calendar").innerHTML=[...groups.values()].map(events=>{
    const d=events[0]._date;
    return `<section class="day"><div class="day-title"><h2>${esc(fmtDay(d))}</h2><span>${events.length} events</span></div>
      <div class="grid">${events.map(eventCard).join("")}</div></section>`;
  }).join("");
  renderHealth();
}

async function init(){
  try{
    const res=await fetch("./data/events.json",{cache:"no-store"});
    if(!res.ok)throw new Error(`HTTP ${res.status}`);
    const payload=await res.json();
    state.data=Array.isArray(payload.events)?payload.events:[];state.meta=payload;
    $("#updated").textContent=payload.updated_at?`Updated ${new Date(payload.updated_at).toLocaleString("uk-UA")}`:"Not updated yet";

    $("#sportFilter").innerHTML=optionHtml(uniq(state.data.map(x=>x.sport)),"All sports");
    $("#groupFilter").innerHTML=optionHtml(uniq(state.data.map(x=>x.competition_group)),"All competition types");
    $("#regionFilter").innerHTML=optionHtml(uniq(state.data.map(x=>x.region)),"All regions");
    $("#leagueFilter").innerHTML=optionHtml(uniq(state.data.map(x=>x.league)),"All competitions");
    $("#stageFilter").innerHTML=optionHtml(uniq(state.data.map(x=>x.stage)),"All stages");
    $("#reasonFilter").innerHTML=optionHtml(uniq(state.data.flatMap(x=>x.priority_tags||[])),"All priority reasons");
    setRange(Number(payload.default_view_days||30));
  }catch(err){
    $("#updated").textContent="Could not load events";
    $("#calendar").innerHTML=`<div class="empty"><strong>Could not load data.</strong><span>${esc(err.message)}</span></div>`;
    console.error(err);
  }
}

$("#search").addEventListener("input",e=>{state.search=e.target.value;render()});
$("#sportFilter").addEventListener("change",e=>{state.sport=e.target.value;render()});
$("#groupFilter").addEventListener("change",e=>{state.group=e.target.value;render()});
$("#regionFilter").addEventListener("change",e=>{state.region=e.target.value;render()});
$("#leagueFilter").addEventListener("change",e=>{state.league=e.target.value;render()});
$("#stageFilter").addEventListener("change",e=>{state.stage=e.target.value;render()});
$("#reasonFilter").addEventListener("change",e=>{state.reason=e.target.value;render()});
$("#scoreFilter").addEventListener("change",e=>{state.minScore=Number(e.target.value||0);render()});
$("#drcOnly").addEventListener("change",e=>{state.drcOnly=e.target.checked;render()});
$("#topOnly").addEventListener("change",e=>{state.topOnly=e.target.checked;render()});
$("#dateFrom").addEventListener("change",e=>{state.from=startOfDay(e.target.value);$$("[data-days]").forEach(b=>b.classList.remove("active"));render()});
$("#dateTo").addEventListener("change",e=>{state.to=endOfDay(e.target.value);$$("[data-days]").forEach(b=>b.classList.remove("active"));render()});
$$("[data-days]").forEach(b=>b.addEventListener("click",()=>setRange(Number(b.dataset.days))));
$$("[data-mode]").forEach(b=>b.addEventListener("click",()=>{
  state.mode=b.dataset.mode;$$("[data-mode]").forEach(x=>x.classList.toggle("active",x===b));render();
}));
init();
