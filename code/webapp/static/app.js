'use strict';
const $ = id => document.getElementById(id);
const palette = ['#0a8e82','#5984c2','#e2a14e','#ad70ad','#6eac6a','#d57676','#9aa8b0'];
const typeColors = {'Epithelial cells':'#5984c2','T cells':'#0a8e82','Myeloids':'#e2a14e','B cells':'#ad70ad','Stromal cells':'#6eac6a','Mast cells':'#d57676','Uncertain':'#aab6be'};
let data, reference, spatial, statePlot, spatialPlot, activePage = 'overview', nicheFilter = -1;
let stateGeneResult = null, spatialGeneResult = null, expressionRequest = 0, geneListRequest = 0, polling = null;
const nf = new Intl.NumberFormat('zh-CN');
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const percent = value => `${(value*100).toFixed(1)}%`;
const typeName = key => data.type_names[key] || key;
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('toast').hidden = true, 3600); }
async function getJSON(url, options) { const response = await fetch(url, options); if (!response.ok) { let detail; try { detail=await response.json(); } catch {} throw new Error(detail?.error || `请求失败 (${response.status})`); } return response.json(); }
function download(url, filename) { const a = document.createElement('a'); a.href = url; if (filename) a.download = filename; a.click(); }
function continuous(value, min, max) { const t = Math.max(0, Math.min(1, (value-min)/(max-min || 1))); const a=[219,239,234], b=[0,119,112]; return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*t)).join(',')})`; }

class Scatter {
  constructor(canvas, tooltip, select) {
    this.canvas = canvas; this.tooltip = tooltip; this.select = select; this.zoom = 1; this.pan = [0,0]; this.selected = -1; this.positions=[];
    canvas.tabIndex = 0;
    new ResizeObserver(() => this.draw()).observe(canvas.parentElement);
    canvas.addEventListener('wheel', event => { if(!this.points)return; event.preventDefault(); this.zoom=Math.max(1,Math.min(15,this.zoom*(event.deltaY<0?1.15:1/1.15))); this.draw(); }, {passive:false});
    canvas.addEventListener('pointerdown', event=>{this.down=[event.clientX,event.clientY];this.last=this.down;this.dragged=0;canvas.setPointerCapture(event.pointerId);});
    canvas.addEventListener('pointermove', event=>{
      const rect=canvas.getBoundingClientRect(), x=event.clientX-rect.left,y=event.clientY-rect.top;
      if(this.down){const dx=event.clientX-this.last[0],dy=event.clientY-this.last[1];this.pan[0]+=dx;this.pan[1]+=dy;this.last=[event.clientX,event.clientY];this.dragged+=Math.abs(dx)+Math.abs(dy);this.tooltip.hidden=true;this.draw();return;}
      const nearest=this.nearest(x,y); if(nearest<0){this.tooltip.hidden=true;return;}
      this.tooltip.textContent=this.tooltipText(nearest);this.tooltip.style.left=`${Math.min(x+12,Math.max(0,rect.width-240))}px`;this.tooltip.style.top=`${Math.max(0,y-40)}px`;this.tooltip.hidden=false;
    });
    canvas.addEventListener('pointerup', event=>{if(!this.down)return;const rect=canvas.getBoundingClientRect();if(this.dragged<5){const i=this.nearest(event.clientX-rect.left,event.clientY-rect.top);if(i>=0)this.choose(i);}this.down=null;});
    canvas.addEventListener('pointerleave',()=>this.tooltip.hidden=true);
    canvas.addEventListener('pointercancel',()=>this.down=null);
    canvas.addEventListener('keydown',event=>{if(!this.points)return;if(['ArrowRight','ArrowLeft'].includes(event.key)){event.preventDefault();this.choose((Math.max(0,this.selected)+(event.key==='ArrowRight'?1:this.points.length-1))%this.points.length);}if(event.key==='Home'){event.preventDefault();this.reset();}});
  }
  choose(i){this.selected=i;this.select(i);this.draw();}
  clear(message){this.points=null;this.positions=[];this.selected=-1;this.tooltip.hidden=true;const ctx=this.canvas.getContext('2d'),dpr=window.devicePixelRatio||1;ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,this.canvas.width,this.canvas.height);ctx.scale(dpr,dpr);ctx.fillStyle='#6c828f';ctx.font='15px "Microsoft YaHei",sans-serif';ctx.textAlign='center';ctx.fillText(message,this.canvas.clientWidth/2,this.canvas.clientHeight/2);}
  reset(){this.zoom=1;this.pan=[0,0];this.draw();}
  set(points, colors, options={}){this.points=points;this.colors=colors;this.options=options;this.selected=-1;this.tooltip.hidden=true;this.tooltipText=options.tooltip || (i=>`细胞 ${i+1}`);if(options.reset)this.reset();else this.draw();}
  nearest(x,y){let idx=-1,best=90;for(let i=0;i<this.positions.length;i++){const p=this.positions[i];if(!p)continue;const d=(p[0]-x)**2+(p[1]-y)**2;if(d<best){best=d;idx=i;}}return idx;}
  draw(){
    if(!this.points || this.canvas.clientWidth<10)return;
    const width=this.canvas.clientWidth,height=this.canvas.clientHeight,dpr=window.devicePixelRatio||1;
    this.canvas.width=width*dpr;this.canvas.height=height*dpr;const ctx=this.canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.fillStyle='#fff';ctx.fillRect(0,0,width,height);
    const pad={left:54,right:18,top:15,bottom:42},pw=width-pad.left-pad.right,ph=height-pad.top-pad.bottom;
    let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
    for(const [x,y] of this.points){xmin=Math.min(xmin,x);xmax=Math.max(xmax,x);ymin=Math.min(ymin,y);ymax=Math.max(ymax,y);}
    const dx=xmax-xmin||1,dy=ymax-ymin||1;
    ctx.font='11px "Segoe UI",sans-serif';ctx.strokeStyle='#edf2f5';ctx.lineWidth=1;ctx.fillStyle='#92a1ad';
    for(let j=0;j<=4;j++){const x=pad.left+pw*j/4,y=pad.top+ph*j/4;ctx.beginPath();ctx.moveTo(x,pad.top);ctx.lineTo(x,pad.top+ph);ctx.stroke();ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+pw,y);ctx.stroke();if(this.zoom===1&&Math.abs(this.pan[0])+Math.abs(this.pan[1])<1){ctx.textAlign='center';ctx.fillText((xmin+dx*j/4).toFixed(this.options.spatial?0:1),x,height-22);ctx.textAlign='right';ctx.fillText((this.options.spatial?ymin+dy*j/4:ymax-dy*j/4).toFixed(this.options.spatial?0:1),pad.left-9,y+4);}}
    ctx.save();ctx.beginPath();ctx.rect(pad.left,pad.top,pw,ph);ctx.clip();this.positions=[];
    for(let i=0;i<this.points.length;i++){
      const point=this.points[i],nx=(point[0]-xmin)/dx,ny=(point[1]-ymin)/dy;
      const px=pad.left+pw/2+(nx-.5)*pw*this.zoom+this.pan[0],py=pad.top+ph/2+((this.options.spatial?ny:1-ny)-.5)*ph*this.zoom+this.pan[1];
      this.positions.push([px,py]);ctx.globalAlpha=this.options.opacity?this.options.opacity(i):.83;ctx.fillStyle=this.colors[i];ctx.beginPath();ctx.arc(px,py,this.options.spatial?Math.min(3.5,1.8*Math.sqrt(this.zoom)):2.1,0,Math.PI*2);ctx.fill();
    }
    ctx.globalAlpha=1;if(this.selected>=0){const p=this.positions[this.selected];ctx.strokeStyle='#12374b';ctx.lineWidth=2;ctx.beginPath();ctx.arc(p[0],p[1],6,0,Math.PI*2);ctx.stroke();}ctx.restore();
    ctx.fillStyle='#8a9ba7';ctx.textAlign='right';ctx.font='11px "Microsoft YaHei",sans-serif';ctx.fillText(this.options.spatial?'来源坐标 x':'PC 1',width-pad.right,height-3);
  }
  save(name){const a=document.createElement('a');a.href=this.canvas.toDataURL('image/png');a.download=name;a.click();}
}

function showPage(page){
  activePage=page;document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.id===`page-${page}`));
  document.querySelectorAll('.nav').forEach(el=>el.classList.toggle('active',el.dataset.page===page));
  $('pageCrumb').textContent={overview:'数据概览',states:'细胞状态与代谢',spatial:'空间与生态位',methods:'分析流程与记录',agent:'智能体'}[page];
  history.replaceState(null,'',`#${page}`);requestAnimationFrame(()=>{if(page==='states')renderState();if(page==='spatial')renderSpatial();});
}
function barList(counts, element, denominator){
  const rows=Object.entries(counts).sort((a,b)=>b[1]-a[1]),total=denominator ?? rows.reduce((s,[,n])=>s+n,0);
  element.innerHTML=rows.map(([name,n])=>`<div class="bar-row"><div class="bar-head"><strong>${esc(typeName(name))}</strong><span>${nf.format(n)} · ${percent(n/(total||1))}</span></div><div class="bar-track"><div class="bar-fill" style="width:${n/(total||1)*100}%;background:${typeColors[name]||'#678a9e'}"></div></div></div>`).join('');
}
function legend(element, entries){element.innerHTML=entries.map(([name,color])=>`<span><i style="background:${color}"></i>${esc(name)}</span>`).join('');}
function continuousLegend(element,min,max,label){element.innerHTML=`<span>${esc(label)}</span><span>${min.toFixed(2)}<i class="continuous-legend"></i>${max.toFixed(2)}</span>`;}
function pipeline(element, full=false){
  const steps=[['输入校验','计数、细胞ID和空间坐标对齐',true],['细胞类型映射','497个共有基因 · 按患者留出验证',true],['空间邻域与生态位基线','12 / 24近邻 · 3至6类GMM',true],['双分支 GNN','自身状态、环境表示与独立患者比较',false]];
  element.innerHTML=steps.map(([title,description,done])=>`<div class="step ${done?'':'pending'}"><span class="step-icon">${done?'✓':'○'}</span><div><strong>${title}</strong><p>${description}</p></div></div>`).join('');
}
function renderOverview(){
  const total=data.datasets.reduce((s,d)=>s+d.cells,0);
  $('overviewMetrics').innerHTML=[['输入细胞',nf.format(total),'单细胞与两份空间裁剪区域'],['空间样本','2','每份约4,000个细胞'],['共有基因',nf.format(data.shared_genes),'用于跨平台细胞类型映射'],['单细胞患者','2','按患者留出验证']].map(([label,value,note])=>`<article class="metric"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-note">${note}</div></article>`).join('');
  $('updatedAt').textContent=`计算于 ${new Date(data.created_at).toLocaleString('zh-CN')}`;
  $('datasetCards').innerHTML=data.datasets.map(d=>`<div class="dataset-card"><div class="dataset-icon">${d.modality==='scrna'?'◉':'⌘'}</div><div><h3>${esc(d.name)}</h3><p>${nf.format(d.cells)} 个细胞 · ${nf.format(d.genes)} 个基因</p><small>${d.modality==='scrna'?'表达与原作者注释':'细胞表达与空间坐标'}</small></div><button class="icon-button dataset-open" data-id="${esc(d.id)}">查看</button></div>`).join('');
  document.querySelectorAll('.dataset-open').forEach(button=>button.onclick=()=>{const d=data.datasets.find(v=>v.id===button.dataset.id);if(d.modality==='scrna')showPage('states');else{$('spatialSample').value=d.id;spatial=d;nicheFilter=-1;spatialGeneResult=null;showPage('spatial');}});
  pipeline($('pipelineCompact'));
}
function renderState(){
  const mode=$('stateColor').value;let colors;
  if(mode==='type'){colors=reference.labels.map(v=>typeColors[v]);legend($('stateLegend'),Object.keys(reference.type_counts).map(t=>[typeName(t),typeColors[t]]));}
  else if(mode==='patient'){const patients=[...new Set(reference.patients)];colors=reference.patients.map(v=>palette[patients.indexOf(v)]);legend($('stateLegend'),patients.map((v,i)=>[v,palette[i]]));}
  else{
    let values,label;
    if(mode==='gene'){
      if(!stateGeneResult?.measured){$('stateStatus').textContent=stateGeneResult?'该基因未列于此矩阵':'输入基因并点击显示';statePlot.clear($('stateStatus').textContent);$('stateLegend').textContent='';return;}
      values=stateGeneResult.values.map(Math.log1p);label=`${stateGeneResult.gene} · log1p原始计数`;
    }else{const p=mode.split(':')[1];values=reference.program_scores[p];label=data.programs[p];}
    if(!values){toast('该程序的可测基因覆盖不足');return;}
    const min=Math.min(...values),max=Math.max(...values);colors=values.map(v=>continuous(v,min,max));continuousLegend($('stateLegend'),min,max,label);
  }
  $('stateStatus').textContent=mode==='gene'?`检测到 ${percent(stateGeneResult.positive/stateGeneResult.cells)} 的细胞`:'2,709个细胞 · 所有细胞类型保留';
  statePlot.set(reference.coords,colors,{tooltip:i=>`${reference.cell_ids[i]} · ${typeName(reference.labels[i])}`});
}
function stateDetail(i){
  const rows=[['细胞ID',reference.cell_ids[i]],['细胞类型',typeName(reference.labels[i])],['患者',reference.patients[i]]];
  for(const [p,values] of Object.entries(reference.program_scores))rows.push([data.programs[p],values[i].toFixed(3)]);
  if(stateGeneResult?.measured)rows.push([`${stateGeneResult.gene}计数`,stateGeneResult.values[i]]);
  $('stateDetail').classList.remove('empty');$('stateDetail').innerHTML=`<dl>${rows.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`;
}
function renderHeatmap(){
  const programs=Object.keys(reference.score_summary),types=Object.keys(reference.type_counts);
  $('programHeatmap').innerHTML=`<table><thead><tr><th>细胞类型</th>${programs.map(p=>`<th>${esc(data.programs[p])}</th>`).join('')}</tr></thead><tbody>${types.map(t=>`<tr><td>${esc(typeName(t))}</td>${programs.map(p=>{const values=Object.values(reference.score_summary[p]),v=reference.score_summary[p][t];return `<td class="heat" style="background:${continuous(v,Math.min(...values),Math.max(...values))};color:${v>(Math.min(...values)+Math.max(...values))/2?'white':'#23514c'}">${v.toFixed(2)}</td>`;}).join('')}</tr>`).join('')}</tbody></table>`;
}
function nicheModel(){return spatial.niche_models[`${$('neighbors').value}_${$('clusters').value}`];}
function renderSpatial(){
  const mode=$('spatialColor').value,model=nicheModel(),k=Number($('clusters').value);let colors;
  if(mode==='niche'){colors=model.labels.map(v=>palette[v]);legend($('spatialLegend'),Array.from({length:k},(_,i)=>[`生态位 ${i+1}`,palette[i]]));}
  else if(mode==='type'){colors=spatial.labels.map(v=>typeColors[v]);legend($('spatialLegend'),Object.keys(spatial.type_counts).map(t=>[typeName(t),typeColors[t]]));}
  else{
    let values,label;
    if(mode==='gene'){
      if(!spatialGeneResult?.measured){$('spatialStatus').textContent=spatialGeneResult?'该基因未列于此面板':'输入基因并点击显示';spatialPlot.clear($('spatialStatus').textContent);$('spatialLegend').textContent='';$('spatialPlotTitle').textContent=spatial.name;return;}
      values=spatialGeneResult.values.map(Math.log1p);label=`${spatialGeneResult.gene} · log1p原始计数`;
    }else{values=spatial.support;label='细胞类型映射支持度';}
    const min=Math.min(...values),max=Math.max(...values);colors=values.map(v=>continuous(v,min,max));continuousLegend($('spatialLegend'),min,max,label);
  }
  $('spatialPlotTitle').textContent=spatial.name;
  const unknown=spatial.type_counts.Uncertain||0;
  $('spatialStatus').textContent=`${nf.format(spatial.cells)}个细胞 · 待确认 ${percent(unknown/spatial.cells)} · ${model.converged?'模型已收敛':'模型未收敛'}`;
  spatialPlot.set(spatial.coords,colors,{spatial:true,opacity:i=>(nicheFilter<0||model.labels[i]===nicheFilter) ? .9 : .12,tooltip:i=>`${spatial.cell_ids[i]} · ${typeName(spatial.labels[i])} · 生态位 ${model.labels[i]+1}`});
  $('nicheFilters').innerHTML=[[-1,'全部'],...Array.from({length:k},(_,i)=>[i,`生态位 ${i+1}`])].map(([i,label])=>`<button class="chip ${i===nicheFilter?'active':''}" data-niche="${i}">${label}</button>`).join('');
  document.querySelectorAll('[data-niche]').forEach(button=>button.onclick=()=>{nicheFilter=Number(button.dataset.niche);renderSpatial();});
  const counts={};for(let i=0;i<spatial.cells;i++)if(nicheFilter<0||model.labels[i]===nicheFilter)counts[spatial.labels[i]]=(counts[spatial.labels[i]]||0)+1;
  barList(counts,$('nicheComposition'));
  $('coverageList').innerHTML=Object.entries(spatial.coverage).map(([p,c])=>`<div class="coverage-item"><strong>${esc(c.name)}</strong><span class="${c.available?'available':'unavailable'}">${c.available?'可显示表达评分':'本面板覆盖不足'}</span><small>${c.present.length} / ${c.total} 个程序基因</small><small>${esc(c.present.join('、')||'该程序基因未覆盖')}</small></div>`).join('');
}
function spatialDetail(i){
  const model=nicheModel(),rows=[['细胞ID',spatial.cell_ids[i]],['映射类型',typeName(spatial.labels[i])],['映射支持度',percent(spatial.support[i])],['生态位',`生态位 ${model.labels[i]+1}`],['归属概率',percent(model.support[i])],['空间坐标',spatial.coords[i].join(', ')]];
  if(spatialGeneResult?.measured)rows.push([`${spatialGeneResult.gene}计数`,spatialGeneResult.values[i]]);
  $('spatialDetail').classList.remove('empty');$('spatialDetail').innerHTML=`<dl>${rows.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`;
}
function renderMethods(){
  pipeline($('pipelineFull'),true);
  $('validationCards').innerHTML=data.validation.map(v=>`<div class="validation-card"><h3>留出患者 ${esc(v.patient)} <span class="pill">${nf.format(v.cells)} 个细胞</span></h3><div class="validation-metrics"><span>准确率<strong>${percent(v.accuracy)}</strong></span><span>Macro-F1<strong>${v.macro_f1.toFixed(3)}</strong></span></div></div>`).join('');
  const titles={mapping:'细胞类型映射',scores:'程序表达评分',niche:'生态位基线',confidence:'归属结果',sample_scope:'示例范围'};
  $('methodList').innerHTML=Object.entries(data.methods).map(([k,v])=>`<dt>${titles[k]||esc(k)}</dt><dd>${esc(v)}</dd>`).join('');
}
async function expression(kind){
  const request=++expressionRequest,dataset=kind==='state'?reference:spatial,input=$(kind==='state'?'stateGene':'spatialGene'),gene=input.value.trim();
  if(!gene)return;input.disabled=true;
  try{
    const result=await getJSON(`/api/expression?dataset=${encodeURIComponent(dataset.id)}&gene=${encodeURIComponent(gene)}`);
    if(request!==expressionRequest)return;
    if(kind==='state'){stateGeneResult=result;$('stateColor').value='gene';renderState();}else{spatialGeneResult=result;$('spatialColor').value='gene';renderSpatial();}
    if(!result.measured)toast(`${gene} 未列于当前数据的基因清单`);
  }catch(error){toast(error.message);}finally{input.disabled=false;}
}
async function suggest(kind){
  const request=++geneListRequest,dataset=kind==='state'?reference:spatial,input=$(kind==='state'?'stateGene':'spatialGene'),list=$(kind==='state'?'stateGeneList':'spatialGeneList');
  try{const genes=await getJSON(`/api/genes?dataset=${encodeURIComponent(dataset.id)}&q=${encodeURIComponent(input.value)}`);if(request===geneListRequest)list.innerHTML=genes.map(g=>`<option value="${esc(g)}"></option>`).join('');}catch(error){toast(error.message);}
}
async function checkJob(){
  try{const status=await getJSON('/api/status');$('jobStatus').hidden=false;$('jobStatus').textContent=status.message;$('rebuild').disabled=status.running;if(!status.running){clearInterval(polling);polling=null;if(status.error)toast(status.error);else{await load();toast('已重新计算并更新全部结果');}}}catch(error){clearInterval(polling);polling=null;$('rebuild').disabled=false;$('jobStatus').textContent=error.message;}
}
async function load(){
  data=await getJSON('/api/analysis');reference=data.datasets.find(d=>d.modality==='scrna');const allSpatial=data.datasets.filter(d=>d.modality==='spatial');const chosen=$('spatialSample').value;
  spatial=allSpatial.find(d=>d.id===chosen)||allSpatial[0];$('spatialSample').innerHTML=allSpatial.map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join('');$('spatialSample').value=spatial.id;
  if(!statePlot){statePlot=new Scatter($('stateCanvas'),$('stateTooltip'),stateDetail);spatialPlot=new Scatter($('spatialCanvas'),$('spatialTooltip'),spatialDetail);}
  stateGeneResult=null;spatialGeneResult=null;if($('stateColor').value==='gene')$('stateColor').value='type';if($('spatialColor').value==='gene')$('spatialColor').value='niche';
  renderOverview();barList(reference.type_counts,$('referenceComposition'));renderHeatmap();renderMethods();
  try{$('manifestText').textContent=JSON.stringify(await getJSON('/api/manifest'),null,2);}catch(error){$('manifestText').textContent=error.message;}
  $('loading').hidden=true;$('app').hidden=false;showPage(activePage);
}
document.querySelectorAll('[data-page]').forEach(button=>button.onclick=()=>showPage(button.dataset.page));
document.querySelector('.brand').onclick=event=>{event.preventDefault();showPage('overview');};
$('openSpatial').onclick=()=>showPage('spatial');
$('downloadManifest').onclick=()=>download('/api/manifest','manifest.json');
$('downloadJson').onclick=()=>download('/api/analysis','analysis.json');
document.querySelectorAll('.export').forEach(button=>button.onclick=()=>download(`/api/export?dataset=${encodeURIComponent(button.dataset.export==='reference'?reference.id:spatial.id)}`,'annotations.tsv'));
$('stateColor').onchange=()=>{$('stateColor').value==='gene'?expression('state'):renderState();};
$('spatialColor').onchange=()=>{$('spatialColor').value==='gene'?expression('spatial'):renderSpatial();};
$('spatialSample').onchange=()=>{++expressionRequest;spatial=data.datasets.find(d=>d.id===$('spatialSample').value);spatialGeneResult=null;nicheFilter=-1;spatialPlot.reset();$('spatialDetail').classList.add('empty');$('spatialDetail').textContent='点击空间图中的细胞，查看结果。';if($('spatialColor').value==='gene')expression('spatial');else renderSpatial();};
for(const id of ['neighbors','clusters'])$(id).onchange=()=>{nicheFilter=-1;renderSpatial();$('spatialDetail').classList.add('empty');$('spatialDetail').textContent='参数已更新，点击细胞查看当前结果。';};
for(const kind of ['state','spatial']){const input=$(kind==='state'?'stateGene':'spatialGene');input.oninput=()=>{clearTimeout(input.timer);input.timer=setTimeout(()=>suggest(kind),180);};input.onkeydown=e=>{if(e.key==='Enter')expression(kind);};}
$('showStateGene').onclick=()=>expression('state');$('showSpatialGene').onclick=()=>expression('spatial');
$('saveState').onclick=()=>statePlot.save('cell_state.png');$('saveSpatial').onclick=()=>spatialPlot.save('spatial_niche.png');$('resetSpatial').onclick=()=>spatialPlot.reset();
$('rebuild').onclick=async()=>{try{const status=await getJSON('/api/rebuild',{method:'POST',headers:{'X-Requested-With':'NicheLab'}});$('jobStatus').hidden=false;$('jobStatus').textContent=status.message;$('rebuild').disabled=true;if(!polling)polling=setInterval(checkJob,1200);}catch(error){toast(error.message);}};
let agentHistory=[],agentReady=false;
function agentStatus(status){agentReady=status.configured;$('agentStatus').textContent=agentReady?'已就绪':'待启用';$('agentSend').disabled=!agentReady;if(!agentReady)$('agentNotice').textContent='服务配置完成后即可开始分析。';}
async function agentPost(route,body={}){const result=await getJSON(`/api/agent/${route}`,{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'NicheLab'},body:JSON.stringify({...body,language:window.NicheI18n?.language||'zh'})});if(result.error)throw new Error(result.error);return result;}
function agentBubble(role,text,trace=[]){const el=document.createElement('div');el.className=`agent-message ${role}`;const heading=document.createElement('strong');heading.textContent=role==='user'?'你':'ImmuNiche 助手';const content=document.createElement('div');content.className='agent-text';content.textContent=text;el.append(heading,content);if(trace.length){const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=`查询记录 · ${trace.length} 次`;pre.textContent=JSON.stringify(trace,null,2);details.append(summary,pre);el.append(details);}$('agentMessages').append(el);el.scrollIntoView({block:'nearest'});}
$('agentNew').onclick=()=>{agentHistory=[];$('agentMessages').replaceChildren();};
$('agentChat').onsubmit=async event=>{event.preventDefault();if(!agentReady)return;const question=$('agentQuestion').value.trim();if(!question)return;const historySnapshot=agentHistory.slice();agentBubble('user',question);$('agentQuestion').value='';$('agentSend').disabled=true;$('agentNotice').textContent='正在查询与分析…';try{const result=await agentPost('chat',{message:question,history:historySnapshot,context:{dataset_id:spatial.id,neighbors:Number($('neighbors').value),clusters:Number($('clusters').value)}});agentBubble('assistant',result.answer,result.trace);agentHistory=[...historySnapshot,{role:'user',content:question},{role:'assistant',content:result.answer}].slice(-8);$('agentNotice').textContent=`已完成 · ${result.trace.length} 次工具查询`;}catch(error){agentBubble('assistant',error.message);$('agentNotice').textContent=error.message;}finally{$('agentSend').disabled=!agentReady;}};
$('agentPrompts').querySelectorAll('button').forEach(button=>button.onclick=()=>{$('agentQuestion').value=button.textContent;$('agentQuestion').focus();});
getJSON('/api/agent/status').then(agentStatus).catch(error=>{$('agentNotice').textContent=error.message;});
const initial=location.hash.slice(1);if(['overview','states','spatial','methods','agent'].includes(initial))activePage=initial;
load().catch(error=>{$('loading').hidden=true;$('error').hidden=false;$('error').textContent=`页面暂时无法读取分析结果：${error.message}\n请确认本地服务正在运行。`;});
