/* Synthetic-only Chrome batch-model validation. No original game data. */
"use strict";
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const assert=require("node:assert/strict");

const controls=new Map();
const document={getElementById(id){
 const el={id,textContent:"",value:"",disabled:true,listeners:{},
  addEventListener(type,fn){this.listeners[type]=fn;}};
 controls.set(id,el);
 return el;
}};
const context=vm.createContext({document,gl:null,program:null});
const files=["original-hotel-props.js","original-hotel-batch.js"];
for(const file of files)
 vm.runInContext(fs.readFileSync(path.join(__dirname,"../../docs",file),"utf8"),context);
const model="models/props_furniture/hotel_chair.mdl";
const records=[
 {class:"prop_static",model,origin:[10,20,30],angles:[0,90,0]},
 {class:"prop_static",model,origin:[50,60,70],angles:[0,0,0]}
];
const scene={format:"lfd2-original-hotel-studio-bundle-v1",
 source_map:"c1m1_hotel.360.bsp",
 models:[{model,file:"models/0123456789abcdef01234567.mesh.json",
          vertices:3,triangles:1,placements:2}],
 placements:records};
const listed=context.batchValidateScene(scene);
assert.equal(listed.size,1);
const matrix=context.batchInstancesFor(records);
assert.equal(matrix.length,24);
const expected=[10,20,30,0,1,0,-1,0,0,0,0,1];
for(let i=0;i<12;i++)assert.ok(Math.abs(expected[i]-matrix[i])<1e-6);
assert.deepEqual(Array.from(matrix.slice(12,24)),[50,60,70,1,0,0,0,1,0,0,0,1]);
assert.throws(()=>context.batchValidateScene({...scene,placements:[
 {...records[0],model:"models/missing/nope.mdl"}]}),/Invalid original batch/);
assert.throws(()=>context.batchValidateScene({...scene,models:[
 {...scene.models[0],file:"../../escape.json"}]}),/Invalid or repeated/);
const mesh={format:"lfd2-source-original-model-v1",model,
 vertices:[0,0,0,1,0,0,0,1,0],normals:[0,0,1,0,0,1,0,0,1],
 indices:[0,1,2]};
assert.equal(context.batchValidateMesh(mesh,model),mesh);
assert.throws(()=>context.batchValidateMesh({...mesh,indices:[0,1,3]},model),
 /vertex\/index bounds/);
assert.deepEqual(Array.from(context.batchColor(model)),Array.from(context.batchColor(model)));
const patterned={...mesh,indices:[0,1,2,0,2,1,2,1,0],
 uvs:[0,0,1,0,0,1],triangle_material_ids:[3,1,3]};
assert.equal(context.batchValidateMesh(patterned,model),patterned);
const grouping=context.batchGroupIndices(patterned);
assert.deepEqual(Array.from(grouping.indices),[0,1,2,2,1,0,0,2,1]);
assert.deepEqual(Array.from(grouping.groups).map(x=>[x.slot,x.count,x.offsetBytes]),
 [[3,6,0],[1,3,24]]);
assert.throws(()=>context.batchValidateMesh({...patterned,uvs:[0]},model),
 /vertex\\/index\\/material\\/UV bounds/);
const textureManifest={format:"lfd2-original-hotel-provisional-model-textures-v1",
 models:[{model,slot:3,texture:"models/furniture/chair",
    png:"textures/models/furniture/chair.png",
    mapping:"PROVISIONAL_EXACT_FILENAME_NOT_VMT_VERIFIED"}]};
assert.equal(context.batchValidateTextureManifest(textureManifest).length,1);
assert.throws(()=>context.batchValidateTextureManifest({...textureManifest,models:[
 {...textureManifest.models[0],png:"textures/../unsafe.png"}]}),/Invalid or duplicate/);
assert.throws(()=>context.batchValidateTextureManifest({...textureManifest,models:[
 textureManifest.models[0],textureManifest.models[0]]}),/Invalid or duplicate/);
assert.ok(controls.get("originalBatchFolder").listeners.change);
assert.ok(controls.get("originalNextModel").listeners.click);
assert.ok(controls.get("originalBatchTextureFolder").listeners.change);
console.log("Offline original hotel batch model folder validation and GPU instance transforms passed");
