/* Streamlit Components v1 protocol; API credentials stay in Python. */
(() => {
  let initialized=false, current=null, serial=0;
  let resolveBoot;
  const bootReady=new Promise(resolve=>resolveBoot=resolve),queue=[],pending=new Map();
  const session=crypto.randomUUID();
  const post=(type,extra={})=>window.parent.postMessage({isStreamlitMessage:true,type,...extra},'*');
  const response=reply=>new Response(typeof reply.data==='string'&&reply.content_type?reply.data:JSON.stringify(reply.data),{status:reply.status||200,headers:{'Content-Type':reply.content_type||'application/json; charset=utf-8'}});
  function pump(){if(current||!queue.length)return;current=queue.shift();post('streamlit:setComponentValue',{dataType:'json',value:current.request});}
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async(url,options={})=>{
    if(typeof url!=='string'||!url.startsWith('/api/'))return nativeFetch(url,options);
    const boot=await bootReady;
    if((!options.method||options.method==='GET')&&Object.hasOwn(boot,url))return response({data:boot[url]});
    return new Promise((resolve,reject)=>{const id=`${session}:${++serial}`;const item={request:{id,url,method:options.method||'GET',body:options.body||''},resolve,reject};pending.set(id,item);queue.push(item);pump();});
  };
  window.addEventListener('message',event=>{
    if(event.source!==window.parent||event.data?.type!=='streamlit:render')return;
    const args=event.data.args||{};
    if(!initialized){initialized=true;resolveBoot(args.bootstrap||{});const rebuild=document.getElementById('rebuild');if(rebuild){rebuild.disabled=true;rebuild.textContent='基线已完成';}const badge=document.querySelector('.local-badge');if(badge)badge.textContent='在线运行';post('streamlit:setFrameHeight',{height:Math.max(680,Math.min(1050,screen.availHeight-150))});}
    const reply=args.reply;
    if(reply&&pending.has(reply.id)){const item=pending.get(reply.id);pending.delete(reply.id);current=null;item.resolve(response(reply));pump();}
  });
  post('streamlit:componentReady',{apiVersion:1});
})();
