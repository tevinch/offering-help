import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { pathToFileURL } from 'node:url';

export function createExampleServer() {
  const records=[];
  const root=resolve('dist');
  const server=createServer(async(request,response)=>{
    if(request.method==='POST' && request.url==='/check') {
      let body='';
      for await(const chunk of request) body+=chunk;
      let payload,status=200;
      try { payload=JSON.parse(body); } catch { status=400; }
      if(typeof payload?.value!=='string'||!/^\d+$/.test(payload.value)) status=400;
      records.push({body,payload,status});
      response.writeHead(status,{'Content-Type':'application/json'}).end(JSON.stringify(status===200?{value:payload.value}:{error:'Expected an unsigned integer string.'}));
      return;
    }
    try {
      const pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname);
      const file=resolve(root,pathname==='/'?'index.html':'.'+pathname);
      if(!file.startsWith(root+'/'))throw Error('Outside example');
      response.setHeader('Content-Type',extname(file)==='.html'?'text/html':extname(file)==='.js'?'text/javascript':'application/octet-stream');
      response.setHeader('Cache-Control','no-store');
      response.end(await readFile(file));
    } catch { response.writeHead(404).end('Not found'); }
  });
  return {server,records};
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  createExampleServer().server.listen(4179,'127.0.0.1',()=>console.log('Open http://127.0.0.1:4179'));
}
