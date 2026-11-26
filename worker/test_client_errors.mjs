import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

test('request errors preserve the safe server error message',async()=>{
  const source=readFileSync('code/webapp/static/app.js','utf8');
  const helper=source.slice(source.indexOf('async function getJSON('),source.indexOf('\nfunction download('));
  const context=vm.createContext({fetch:async()=>new Response('{"error":"本次对话过长，请开始新对话后重试。"}',{status:400})});
  vm.runInContext(helper,context);
  await assert.rejects(context.getJSON('/api/agent/chat'),/本次对话过长/);
});
