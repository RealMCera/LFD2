/* Synthetic-only Node tests for the browser's private texture folder matcher.
   No images, network, or real Left 4 Dead 2 game files required. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const script=fs.readFileSync(path.join(__dirname,"../../docs/finish-texture-folder.js"),"utf8");
const refs=new Map();
const document={
 getElementById(id) {
  if(!refs.has(id))refs.set(id,{value:"",textContent:"",addEventListener(){}});
  return refs.get(id);
 }
};
const sandbox={
 document,mmMesh:null,createImageBitmap:async()=>({width:512,height:512,close(){}}),
 mmTextures:new Map(),MM_MAX_TOTAL:256,MM_MAX_PNG_BYTES:40*1024*1024,
 mmPixels:0,MM_MAX_TOTAL_PIXELS:80*1024*1024,
 mmInitEntry:()=>({count:3,pixels:512*512}),
 mmEnabled:true,mmToggle:{textContent:""},
 mmStatus:{textContent:""},updateMaterialCoverage(){}
};
const context=vm.createContext(sandbox);
vm.runInContext(script,context);
const file=(name,rel=name)=>({
 name,size:1024,webkitRelativePath:"hotel-complete/"+rel,
 text:async()=>JSON.stringify({format:"lfd2-private-texture-manifest-v1"})
});
const mesh={materials:["PLASTER/PLASTER_INT_14",
                       "MAPS/C1M1_HOTEL/C-200_5022_1257.HDR"]};
const manifest={
 format:"lfd2-private-texture-manifest-v1",
 materials:{
  "plaster/plaster_int_14":"textures/plaster/plaster_int_14.png",
  "maps/c1m1_hotel/c-200_5022_1257.hdr":
    "textures/maps/c1m1_hotel/c-200_5022_1257.hdr.png",
  "missing/some_material":"textures/missing/not_found.png"
 }
};
const files=[
 file("texture-manifest.json"),
 file("plaster_int_14.png","textures/plaster/plaster_int_14.png"),
 file("c-200_5022_1257.hdr.png",
      "textures/maps/c1m1_hotel/c-200_5022_1257.hdr.png")
];
const result=context.finishPlanFiles(files,manifest,mesh);
assert.equal(result.work.length,2,"Matches two original material names exactly");
assert.equal(result.work[0].materialId,0);
assert.equal(result.work[1].materialId,1);
assert.equal(result.missing.length,0,"Unknown mesh materials must not require PNG");
assert.equal(context.finishNormalizedPath("../outside.png"),null);
assert.equal(context.finishNormalizedPath("textures/../../secret.png"),null);
assert.equal(context.finishNormalizedPath("textures/concrete/floor.png"),
             "textures/concrete/floor.png");
assert.throws(()=>context.finishPlanFiles(files,{},mesh),/Unsupported private texture manifest/);
assert.deepEqual(
 Array.from(context.finishPlanFiles(files,{
  format:"lfd2-private-texture-manifest-v1",
  materials:{"plaster/plaster_int_14":"textures/no.png"}
 },mesh).missing),["plaster/plaster_int_14"]);
console.log("Hotel texture folder manifest tests passed.");
