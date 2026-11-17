const $=id=>document.getElementById(id);let quests=[];let map,markers;
const SOURCES={poke:"https://pokexperience.com/field-research/",free:"https://github.com/bilde2910/FreeField"};
function safe(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function validCoords(q){return q.verified===true&&Number.isFinite(Number(q.lat))&&Number.isFinite(Number(q.lng))&&Math.abs(Number(q.lat))<=90&&Math.abs(Number(q.lng))<=180;}
function norm(v){return String(v||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim();}
function matches(hay,needle){if(!needle)return true;const h=norm(hay),n=norm(needle);return h.includes(n)||n.split(" ").filter(Boolean).every(w=>h.includes(w));}
function initMap(){if(!window.L||map)return;map=L.map("map").setView([0,0],2);L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap"}).addTo(map);markers=L.layerGroup().addTo(map);}
function render(){
 const task=$("taskSelect").value||$("taskText").value,reward=$("rewardSelect").value||$("rewardText").value,city=$("city").value,country=$("country").value;
 const found=quests.filter(q=>matches(q.task,task)&&matches(q.reward,reward)&&matches(q.city,city)&&matches(q.country,country));
 $("count").textContent=found.length+" registro(s) correspondente(s) na base própria";
 $("list").innerHTML=found.length?found.map(q=>'<article class="quest"><h3>'+safe(q.task||"Missão sem descrição")+'</h3><p><strong>Recompensa:</strong> '+safe(q.reward||"Não informada")+'</p><p>'+[q.city,q.country].filter(Boolean).map(safe).join(", ")+'</p><p><span class="pill">'+(validCoords(q)?"Coordenadas encontradas junto ao registro":"Sem coordenadas verificadas")+'</span></p>'+(validCoords(q)?'<p>📍 '+safe(q.lat)+", "+safe(q.lng)+' <button class="copy-coord secondary" data-coord="'+safe(q.lat+","+q.lng)+'">Copiar</button></p>':"")+(q.source?'<p><a href="'+safe(q.source)+'" target="_blank" rel="noopener">Ver publicação original</a></p>':"")+'<p class="muted">Atualização: '+safe(q.updated_at||q.discovered_at||"Não informada")+'</p></article>').join(""):'<div class="empty">Nenhum registro corresponde aos filtros na base própria. A cobertura é parcial; consulte também o catálogo comunitário externo.</div>';
 if(markers){markers.clearLayers();const points=found.filter(validCoords);points.forEach(q=>L.marker([Number(q.lat),Number(q.lng)]).addTo(markers).bindPopup("<b>"+safe(q.task)+"</b><br>"+safe(q.reward)));if(points.length)map.fitBounds(points.map(q=>[Number(q.lat),Number(q.lng)]),{padding:[25,25],maxZoom:12});}
 document.querySelectorAll(".copy-coord").forEach(b=>b.addEventListener("click",()=>navigator.clipboard?.writeText(b.dataset.coord).then(()=>b.textContent="Copiado").catch(()=>{})));
}
async function load(force=false){
 initMap();$("count").textContent="Carregando base…";
 try{const r=await fetch("data/quests.json"+(force?"?t="+Date.now():""),{cache:force?"no-store":"default"});if(!r.ok)throw Error("HTTP "+r.status);const d=await r.json();quests=Array.isArray(d)?d:[];$("updated").textContent=quests.length+" registro(s) na base";}catch(e){quests=[];$("updated").textContent="Não foi possível carregar a base";}
 try{const r=await fetch("data/collection-status.json"+(force?"?t="+Date.now():""),{cache:force?"no-store":"default"});const s=await r.json();$("collectorStatus").textContent=s.last_run_utc?"Última coleta: "+new Date(s.last_run_utc).toLocaleString()+" · "+(s.new_verified_records||0)+" novos · "+(s.total_records||0)+" no total · cobertura parcial":"Coletor ainda não registrou uma execução.";}catch(e){$("collectorStatus").textContent="Status da coleta indisponível";}
 render();
}
$("search").addEventListener("click",render);$("refresh").addEventListener("click",()=>load(true));
$("clear").addEventListener("click",()=>{["taskSelect","rewardSelect","country","city","taskText","rewardText"].forEach(id=>$(id).value="");render();});
$("imageInput").addEventListener("change",()=>{const f=$("imageInput").files[0],p=$("imagePreview");if(!f){p.hidden=true;return;}p.src=URL.createObjectURL(f);p.hidden=false;});
const TASK_HINTS=[["excellent","jogada excelente"],["great","ótima jogada"],["curveball","curva"],["catch","captur"],["spin","gire"],["gift","presente"],["raid","reide"],["max battle","batalha max"],["power up","fortale"],["hatch","ovo"],["walk","caminh"],["evolve","evolu"],["transfer","transfira"]];
const REWARD_HINTS=[["eternatus","Eternatus"],["rare candy","doce raro"],["candy xl","doce XL"],["stardust","poeira estelar"],["mega energy","energia mega"],["pokeball","Poké Bola"],["potion","poção"]];
$("readImage").addEventListener("click",async()=>{const f=$("imageInput").files[0];if(!f){$("ocrStatus").textContent="Selecione uma captura de tela primeiro.";return;}if(!window.Tesseract){$("ocrStatus").textContent="O leitor OCR não carregou. Verifique a conexão e tente novamente.";return;}try{$("readImage").disabled=true;$("ocrStatus").textContent="Lendo imagem…";const result=await Tesseract.recognize(f,"por+eng",{logger:m=>{if(m.status==="recognizing text")$("ocrStatus").textContent="Reconhecendo texto: "+Math.round((m.progress||0)*100)+"%";}});const raw=result.data.text.trim(),n=norm(raw),lines=raw.split(/\n+/).map(x=>x.trim()).filter(Boolean);$("ocrText").value=raw;
 let task=lines.find(x=>/excellent|great throw|jogada|capture|catch|spin|gire|send.*gift|present|raid|batalha max|power up|fortale|hatch|egg|walk|caminh|evolve|transfer/i.test(x))||"";
 let reward=lines.find(x=>/eternatus|candy|doces|stardust|poeira|mega energy|energia mega|pok[eé] ball|po[cç][aã]o|potion|revive/i.test(x))||"";
 const taskHint=TASK_HINTS.find(([a,b])=>n.includes(a)||n.includes(norm(b))),rewardHint=REWARD_HINTS.find(([a])=>n.includes(norm(a)));
 $("ocrTask").value=task|| (taskHint?taskHint[1]:"");$("ocrReward").value=reward||(rewardHint?rewardHint[1]:"");
 $("ocrStatus").textContent=raw?"Leitura concluída. Confira os campos — o OCR pode cometer erros.":"Nenhum texto legível encontrado. Tente uma captura mais nítida.";
 }catch(e){$("ocrStatus").textContent="Falha ao reconhecer a imagem. Tente novamente.";}finally{$("readImage").disabled=false;}});
$("useOcr").addEventListener("click",()=>{const task=$("ocrTask").value.trim(),reward=$("ocrReward").value.trim();if(!task&&!reward){$("ocrStatus").textContent="Não encontrei dados. Preencha os campos reconhecidos manualmente.";return;} $("taskSelect").value="";$("rewardSelect").value="";$("taskText").value=task;$("rewardText").value=reward;$("ocrStatus").textContent="Filtros preenchidos. Toque em Buscar na base.";render();});
load();if("serviceWorker"in navigator)window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));
