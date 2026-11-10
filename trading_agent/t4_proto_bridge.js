// T4 protobuf bridge: stdin JSON lines -> stdout JSON lines (base64 binary for send)
const fs = require('fs');
const path = require('path');
const descPath = process.argv[2];
function loadProtobuf() {
  const tries = [
    () => require('protobufjs'),
    () => require(path.join(process.cwd(), 'node_modules', 'protobufjs')),
    () => require(path.join(__dirname, '..', 'node_modules', 'protobufjs')),
    () => require(path.join(__dirname, 'node_modules', 'protobufjs')),
  ];
  for (const t of tries) { try { return t(); } catch (e) {} }
  return null;
}
const protobuf = loadProtobuf();
if (!protobuf) {
  console.log(JSON.stringify({ok:false,error:'protobufjs not found. Install protobufjs in workspace (e.g. npm i protobufjs).'}));
  process.exit(1);
}
try {
  const desc = JSON.parse(fs.readFileSync(descPath, 'utf8'));
  const root = protobuf.Root.fromJSON(desc);
  const CM = root.lookupType('t4proto.v2.service.ClientMessage');
  const SM = root.lookupType('t4proto.v2.service.ServerMessage');
  const OPT = {defaults:true, longs:Number, enums:Number, oneofs:true};
  console.log(JSON.stringify({ok:true}));
  const rl = require('readline').createInterface({input: process.stdin});
  rl.on('line', (line) => {
    let req;
    try {
      req = JSON.parse(line);
      if (req.op === 'encode') {
        const err = CM.verify(req.msg);
        if (err) return console.log(JSON.stringify({id:req.id,error:err}));
        const buf = CM.encode(CM.fromObject(req.msg)).finish();
        console.log(JSON.stringify({id:req.id,bin:Buffer.from(buf).toString('base64')}));
      } else if (req.op === 'decode') {
        const buf = Buffer.from(req.bin, 'base64');
        const msg = SM.toObject(SM.decode(buf), OPT);
        console.log(JSON.stringify({id:req.id,msg}));
      } else if (req.op === 'ping') {
        console.log(JSON.stringify({id:req.id,ok:true}));
      } else {
        console.log(JSON.stringify({id:req.id,error:'unknown op'}));
      }
    } catch (e) {
      console.log(JSON.stringify({id:(req&&req.id)||null,error:String(e&&e.stack||e)}));
    }
  });
  rl.on('close', () => process.exit(0));
} catch (e) {
  console.log(JSON.stringify({ok:false,error:String(e&&e.stack||e)}));
  process.exit(1);
}
