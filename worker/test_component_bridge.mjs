import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

test('component bootstraps locally and serializes API queries',async()=>{
  const sent=[];let listener;
  const parent={postMessage:value=>sent.push(value)};
  const window={parent,fetch:()=>{throw new Error('Unexpected network access')},addEventListener:(type,fn)=>{listener=fn;}};
  const context=vm.createContext({window,crypto:{randomUUID:()=> 'test'},Response,screen:{availHeight:1080},document:{getElementById:()=>null,querySelector:()=>null}});
  vm.runInContext(readFileSync('code/webapp/component_bridge.js','utf8'),context);
  assert.equal(sent[0].type,'streamlit:componentReady');
  listener({source:parent,data:{type:'streamlit:render',args:{bootstrap:{'/api/analysis':{cells:2709}}}}});
  assert.deepEqual(await (await window.fetch('/api/analysis')).json(),{cells:2709});
  const first=window.fetch('/api/genes?dataset=test');
  const second=window.fetch('/api/export?dataset=test');
  await Promise.resolve();
  let request=sent.find(x=>x.type==='streamlit:setComponentValue').value;
  listener({source:parent,data:{type:'streamlit:render',args:{reply:{id:request.id,data:['MPST']}}}});
  assert.deepEqual(await (await first).json(),['MPST']);
  request=sent.filter(x=>x.type==='streamlit:setComponentValue').at(-1).value;
  listener({source:parent,data:{type:'streamlit:render',args:{reply:{id:request.id,data:'cell_id\nx',content_type:'text/tab-separated-values'}}}});
  assert.equal(await (await second).text(),'cell_id\nx');
});
