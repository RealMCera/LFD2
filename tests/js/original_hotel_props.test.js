/* Synthetic-only test of original studio chair transforms in Chrome.
   Run via: node tests/js/original_hotel_props.test.js */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const code=fs.readFileSync(path.join(__dirname,"../../docs/original-hotel-props.js"),"utf8");
const document={getElementById(){return {textContent:"",value:"",
  addEventListener(){}}}};
const context=vm.createContext({document,gl:null,program:null});
vm.runInContext(code,context);
const mesh={format:"lfd2-source-original-model-v1",
 model:"models/props_furniture/hotel_chair.mdl",
 vertices:[0,0,0,4,0,0,0,2,0],
 normals:[0,0,1,0,0,1,0,0,1],
 indices:[0,1,2]};
const actual=context.originalChairValidate(mesh);
assert.equal(actual,mesh);
const p={model:mesh.model,class:"prop_static",
 origin:[10,20,100],angles:[0,90,0]};
const manifest={format:"lfd2-original-prop-placements-v1",placements:[p]};
assert.equal(context.originalPlacementValidate(manifest).length,1);
const view=context.originalChairCamera(p);
assert.ok(Math.abs(view.x-10)<1e-6);
assert.ok(Math.abs(view.y-140)<1e-6);
assert.equal(view.z,156);
assert.ok(Math.abs(view.yaw-1.5*Math.PI)<1e-6);
assert.equal(view.pitch,-0.20);

const result=context.originalChairPacked(mesh,[p]);
assert.equal(result.length,18);
const coords=[result[0],result[1],result[2],
              result[6],result[7],result[8],
              result[12],result[13],result[14]];
for(let i=0;i<coords.length;i++)
 assert.ok(Math.abs(coords[i]-[10,20,100,10,24,100,8,20,100][i])<1e-5);
assert.throws(()=>context.originalChairValidate({...mesh,indices:[0,6,2]}),
              /failed validation/);
assert.throws(()=>context.originalPlacementValidate({
 format:"lfd2-original-prop-placements-v1",placements:[]}),/No valid/);
assert.throws(()=>context.originalChairPacked(
 {...mesh,indices:Array.from({length:600000},()=>0)},
 Array.from({length:2},()=>p)),/Too many triangles/);
console.log("Original chair Source-angle transforms and JSON validation passed");
