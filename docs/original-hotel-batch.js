"use strict";
/* Offline Source studio-model batch renderer. Reads ONE user-selected private
   folder from the existing Xbox local conversion pipeline. Models stay on
   local disk/in Chrome memory. No network fetch and no generated replacements.
   GPU instancing avoids duplicating geometry for hundreds of placements. */
const batchFolderInput=document.getElementById("originalBatchFolder");
const batchStatus=document.getElementById("originalBatchStatus");
const batchNextModel=document.getElementById("originalNextModel");
let batchProgram=null,batchUniform=null,batchEntries=[];
let batchInstances=[],batchCursor=-1;
const BATCH_LIMITS={maxModels:4000,maxPlacements:100000,
 totalBytes:450*1024*1024,maxOne:50*1024*1024,
 totalDrawTriangles:6000000,maxVertices:150000,maxIndices:900000};

function batchValidateMesh(item,path){
 if(!item||item.format!=="lfd2-source-original-model-v1"||
    item.model!==path||
    !Array.isArray(item.vertices)||!Array.isArray(item.normals)||
    !Array.isArray(item.indices)||item.vertices.length>3*BATCH_LIMITS.maxVertices||
    item.indices.length>BATCH_LIMITS.maxIndices||
    item.vertices.length<9||item.vertices.length%3||
    item.vertices.length!==item.normals.length||
    item.indices.length<3||item.indices.length%3)
    throw Error("Invalid authenticated model mesh: "+path);
 const n=item.vertices.length/3;
 if(!item.vertices.every(x=>Number.isFinite(x)&&Math.abs(x)<1e6)||
    !item.normals.every(x=>Number.isFinite(x)&&Math.abs(x)<100)||
    !item.indices.every(x=>Number.isInteger(x)&&x>=0&&x<n))
    throw Error("Invalid original Source vertex/index bounds: "+path);
 return item;
}
function batchValidateScene(data){
 if(!data||data.format!=="lfd2-original-hotel-studio-bundle-v1"||
    data.source_map!=="c1m1_hotel.360.bsp"||
    !Array.isArray(data.models)||!Array.isArray(data.placements)||
    data.models.length<1||data.models.length>BATCH_LIMITS.maxModels||
    data.placements.length>BATCH_LIMITS.maxPlacements)
    throw Error("Expected private offline batch scene.json from hotel converter");
 const dict=new Map();
 for(const item of data.models){
  if(!item||typeof item.model!=="string"||
     !/^models\/[a-z0-9_./-]+\.mdl$/.test(item.model)||
     typeof item.file!=="string"||
     !/^models\/[0-9a-f]{24}\.mesh\.json$/.test(item.file)||
     dict.has(item.model))
     throw Error("Invalid or repeated private Source batch model reference");
  dict.set(item.model,item);
 }
 for(const p of data.placements){
  if(!p||!dict.has(p.model)||
     !Array.isArray(p.origin)||p.origin.length!==3||
     !Array.isArray(p.angles)||p.angles.length!==3||
     ![...p.origin,...p.angles].every(v=>Number.isFinite(v)&&Math.abs(v)<1e6))
     throw Error("Invalid original batch prop placement transform");
 }
 return dict;
}
function batchBasis(angles){
 // Source original studio model local X,Y,Z axes oriented by BSP QAngles.
 return [originalRotate([1,0,0],angles),
         originalRotate([0,1,0],angles),
         originalRotate([0,0,1],angles)];
}
function batchInstancesFor(placements){
 const out=new Float32Array(placements.length*12);
 let offset=0;
 for(const p of placements){
  const basis=batchBasis(p.angles);
  for(const value of [...p.origin,...basis[0],...basis[1],...basis[2]])
   out[offset++]=value;
 }
 return out;
}
function batchShader(){
 if(batchProgram)return;
 const vs=shader(gl.VERTEX_SHADER,[
 "#version 300 es","precision highp float;",
 "in vec3 aPos,aNormal,iOrigin,iBx,iBy,iBz;",
 "uniform vec3 uCamera;","uniform float uYaw,uPitch,uAspect;",
 "out float vLight;",
 "void main(){",
 "vec3 world=iOrigin+iBx*aPos.x+iBy*aPos.y+iBz*aPos.z;",
 "vec3 normal=normalize(iBx*aNormal.x+iBy*aNormal.y+iBz*aNormal.z);",
 "vec3 forward=vec3(cos(uYaw)*cos(uPitch),sin(uYaw)*cos(uPitch),sin(uPitch));",
 "vec3 right=vec3(-sin(uYaw),cos(uYaw),0.0);",
 "vec3 up=cross(forward,right);",
 "vec3 delta=world-uCamera;",
 "vec3 eye=vec3(dot(delta,right),dot(delta,up),dot(delta,forward));",
 "float nearP=2.0,farP=25000.0;",
 "float z=eye.z*(farP+nearP)/(farP-nearP)-(2.0*farP*nearP)/(farP-nearP);",
 "gl_Position=vec4(eye.x*1.35/uAspect,eye.y*1.35,z,eye.z);",
 "vLight=0.45+0.55*abs(dot(normal,normalize(vec3(.4,.2,.9))));",
 "}"
 ].join("\n"));
 const fs=shader(gl.FRAGMENT_SHADER,[
 "#version 300 es","precision highp float;","in float vLight;",
 "uniform vec3 uColor;","out vec4 outColor;",
 "void main(){outColor=vec4(uColor*vLight,1.0);}"
 ].join("\n"));
 const prog=gl.createProgram();gl.attachShader(prog,vs);gl.attachShader(prog,fs);
 gl.linkProgram(prog);
 if(!gl.getProgramParameter(prog,gl.LINK_STATUS))
  throw Error("GPU batch model shader linking failed: "+gl.getProgramInfoLog(prog));
 gl.deleteShader(vs);gl.deleteShader(fs);
 batchProgram=prog;
 batchUniform={
  camera:gl.getUniformLocation(prog,"uCamera"),
  yaw:gl.getUniformLocation(prog,"uYaw"),
  pitch:gl.getUniformLocation(prog,"uPitch"),
  aspect:gl.getUniformLocation(prog,"uAspect"),
  color:gl.getUniformLocation(prog,"uColor")
 };
}
function batchClear(){
 if(gl)for(const e of batchEntries){
  gl.deleteBuffer(e.positions);gl.deleteBuffer(e.indices);
  gl.deleteBuffer(e.instances);gl.deleteVertexArray(e.vao);
 }
 batchEntries=[];batchInstances=[];batchCursor=-1;
 if(batchNextModel)batchNextModel.disabled=true;
}
function batchCreateGpuModel(model,placements){
 batchShader();
 const vertexCount=model.vertices.length/3;
 const interleaved=new Float32Array(vertexCount*6);
 for(let i=0;i<vertexCount;i++){
  for(let j=0;j<3;j++){
   interleaved[i*6+j]=model.vertices[i*3+j];
   interleaved[i*6+3+j]=model.normals[i*3+j];
  }
 }
 const transforms=batchInstancesFor(placements);
 const e={vao:gl.createVertexArray(),positions:gl.createBuffer(),
          indices:gl.createBuffer(),instances:gl.createBuffer(),
          count:model.indices.length,placed:placements.length};
 gl.bindVertexArray(e.vao);
 function attrib(name,size,stride,offset,divisor=0){
  const loc=gl.getAttribLocation(batchProgram,name);
  if(loc<0)throw Error("Missing GPU batch attribute "+name);
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc,size,gl.FLOAT,false,stride,offset);
  gl.vertexAttribDivisor(loc,divisor);
 }
 gl.bindBuffer(gl.ARRAY_BUFFER,e.positions);
 gl.bufferData(gl.ARRAY_BUFFER,interleaved,gl.STATIC_DRAW);
 attrib("aPos",3,24,0);
 attrib("aNormal",3,24,12);
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,e.indices);
 gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(model.indices),gl.STATIC_DRAW);
 gl.bindBuffer(gl.ARRAY_BUFFER,e.instances);
 gl.bufferData(gl.ARRAY_BUFFER,transforms,gl.STATIC_DRAW);
 for(const [name,offset] of [["iOrigin",0],["iBx",12],["iBy",24],["iBz",36]])
  attrib(name,3,48,offset,1);
 gl.bindVertexArray(null);
 return e;
}
function batchColor(name){
 // Repeatable diagnostic model coloring; not the original model material.
 let h=2166136261;
 for(const char of name){h^=char.charCodeAt(0);h=Math.imul(h,16777619);}
 const palette=[[.82,.76,.63],[.81,.64,.47],[.62,.77,.77],
                [.73,.71,.88],[.73,.82,.60],[.82,.67,.69]];
 return palette[(h>>>0)%palette.length];
}
async function batchLoadFolder(filelist){
 const files=Array.from(filelist||[]);
 const bytes=files.reduce((s,f)=>s+f.size,0);
 if(files.length<2||bytes>BATCH_LIMITS.totalBytes)
  throw Error("Select a generated hotel-auto-props folder under 450MB");
 const byPath=new Map();
 for(const file of files){
  if(file.size>BATCH_LIMITS.maxOne)continue;
  let path=file.webkitRelativePath.replace(/\\/g,"/");
  const root=path.split("/")[0];
  path=path.slice(root.length+1);
  if(path)byPath.set(path,file);
 }
 const manifest=byPath.get("scene.json");
 if(!manifest)throw Error("Folder must contain scene.json; choose hotel-auto-props");
 const scene=JSON.parse(await manifest.text());
 const modelByName=batchValidateScene(scene);
 batchClear();
 const grouped=new Map();
 for(const p of scene.placements){
  const existing=grouped.get(p.model)||[];
  existing.push(p);grouped.set(p.model,existing);
 }
 let models=0,triangles=0,skipped=0;
 try{
  for(const [name,meta] of modelByName){
   const f=byPath.get(meta.file);
   if(!f){skipped++;continue;}
   try{
    const model=batchValidateMesh(JSON.parse(await f.text()),name);
    if((model.indices.length/3)*((grouped.get(name)||[]).length)+triangles>
       BATCH_LIMITS.totalDrawTriangles){skipped++;continue;}
    const placements=grouped.get(name)||[];
    if(!placements.length)continue;
    const entry=batchCreateGpuModel(model,placements);
    entry.color=batchColor(name);
    batchEntries.push(entry);
    batchInstances.push({model:name,place:placements[0]});
    models++;
    triangles+=entry.count/3*entry.placed;
   }catch(error){skipped++;if(skipped<4)console.warn("Skipped unsupported source prop",name,error);}
   if(models%20===0&&batchStatus)
    batchStatus.textContent="Importing private original models: "+models+
                            " meshes loaded; "+triangles.toLocaleString()+" triangles";
  }
  if(!models)throw Error("No original model triangles could be loaded from selected folder");
 }catch(error){batchClear();throw error;}
 if(typeof originalPropsReset==="function")originalPropsReset();
 if(batchNextModel)batchNextModel.disabled=false;
 if(batchStatus)batchStatus.textContent=
  "LOADED "+models+" original Source model types; "+
  scene.placements.length+" authored placements in scene; "+
  triangles.toLocaleString()+" real triangle instances drawn; "+
  skipped+" skipped by safety/performance checks. "+
  "Untextured diagnostic shading, no original animated gameplay yet.";
}
function batchNextCamera(){
 if(!mesh||!batchInstances.length)return;
 batchCursor=(batchCursor+1)%batchInstances.length;
 const item=batchInstances[batchCursor];
 Object.assign(cam,originalChairCamera(item.place));
 if(typeof flashHint==="function")
  flashHint("ORIGINAL SOURCE MODEL "+(batchCursor+1)+"/"+batchInstances.length+
            " · "+item.model+" · B NEXT MODEL");
 if(typeof loader!=="undefined"&&loader)loader.style.display="none";
 if(typeof show!=="undefined"&&show)show.style.display="block";
}
if(batchNextModel)batchNextModel.addEventListener("click",batchNextCamera);
if(batchFolderInput)batchFolderInput.addEventListener("change",async()=>{
 try{
  batchStatus.textContent="Loading only local original converted game assets...";
  await batchLoadFolder(batchFolderInput.files);
 }catch(error){
  batchStatus.textContent="Batch import stopped: "+error.message;
 }
 batchFolderInput.value="";
});
function renderOriginalHotelBatch(){
 if(!batchProgram||!batchEntries.length||!gl)return;
 gl.useProgram(batchProgram);
 gl.uniform3f(batchUniform.camera,cam.x,cam.y,cam.z);
 gl.uniform1f(batchUniform.yaw,cam.yaw);
 gl.uniform1f(batchUniform.pitch,cam.pitch);
 gl.uniform1f(batchUniform.aspect,cvs.width/cvs.height);
 for(const item of batchEntries){
  gl.uniform3fv(batchUniform.color,item.color);
  gl.bindVertexArray(item.vao);
  gl.drawElementsInstanced(gl.TRIANGLES,item.count,gl.UNSIGNED_INT,0,item.placed);
 }
 gl.bindVertexArray(null);
 gl.useProgram(program);
}
