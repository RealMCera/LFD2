"use strict";
/* Offline Source studio-model batch renderer. Reads ONE user-selected private
   folder from the existing Xbox local conversion pipeline. Models stay on
   local disk/in Chrome memory. No network fetch and no generated replacements.
   GPU instancing avoids duplicating geometry for hundreds of placements. */
const batchFolderInput=document.getElementById("originalBatchFolder");
const batchStatus=document.getElementById("originalBatchStatus");
const batchNextModel=document.getElementById("originalNextModel");
const batchTextureFolderInput=document.getElementById("originalBatchTextureFolder");
const batchTextureStatus=document.getElementById("originalBatchTextureStatus");
let batchProgram=null,batchUniform=null,batchEntries=[];
let batchInstances=[],batchCursor=-1;
let batchTextureCache=new Map();
const BATCH_TEXTURE_MAX_BYTES=500*1024*1024;
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
    !item.indices.every(x=>Number.isInteger(x)&&x>=0&&x<n)||
    (item.uvs!==undefined&&
      (!Array.isArray(item.uvs)||item.uvs.length!==2*n||
       !item.uvs.every(x=>Number.isFinite(x)&&Math.abs(x)<1e7)))||
    (item.triangle_material_ids!==undefined&&
      (!Array.isArray(item.triangle_material_ids)||
       item.triangle_material_ids.length!==item.indices.length/3||
       !item.triangle_material_ids.every(x=>Number.isInteger(x)&&x>=0&&x<1024))))
    throw Error("Invalid original Source vertex/index/material/UV bounds: "+path);
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
 "in vec3 aPos,aNormal,iOrigin,iBx,iBy,iBz;","in vec2 aUV;",
 "uniform vec3 uCamera;","uniform float uYaw,uPitch,uAspect;",
 "out float vLight;","out vec2 vUV;",
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
 "vUV=aUV;",
 "}"
 ].join("\n"));
 const fs=shader(gl.FRAGMENT_SHADER,[
 "#version 300 es","precision highp float;","in float vLight;","in vec2 vUV;",
 "uniform vec3 uColor;","uniform bool uUseTexture;","uniform sampler2D uTexture;",
 "out vec4 outColor;",
 "void main(){",
 "vec3 color=uUseTexture?texture(uTexture,vUV).rgb:uColor;",
 "outColor=vec4(color*vLight,1.0);",
 "}"
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
  color:gl.getUniformLocation(prog,"uColor"),
  textured:gl.getUniformLocation(prog,"uUseTexture"),
  sampler:gl.getUniformLocation(prog,"uTexture")
 };
}
function batchClear(){
 if(gl)for(const tex of batchTextureCache.values())gl.deleteTexture(tex);
 batchTextureCache.clear();
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
 const interleaved=new Float32Array(vertexCount*8);
 for(let i=0;i<vertexCount;i++){
  for(let j=0;j<3;j++){
   interleaved[i*8+j]=model.vertices[i*3+j];
   interleaved[i*8+3+j]=model.normals[i*3+j];
  }
  interleaved[i*8+6]=(model.uvs||[])[i*2]||0;
  interleaved[i*8+7]=(model.uvs||[])[i*2+1]||0;
 }
 const grouped=batchGroupIndices(model);
 const transforms=batchInstancesFor(placements);
 const e={vao:gl.createVertexArray(),positions:gl.createBuffer(),
          indices:gl.createBuffer(),instances:gl.createBuffer(),
          count:model.indices.length,placed:placements.length,
          groups:grouped.groups,materialTextures:new Map()};
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
 attrib("aPos",3,32,0);
 attrib("aNormal",3,32,12);
 attrib("aUV",2,32,24);
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,e.indices);
 gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,grouped.indices,gl.STATIC_DRAW);
 gl.bindBuffer(gl.ARRAY_BUFFER,e.instances);
 gl.bufferData(gl.ARRAY_BUFFER,transforms,gl.STATIC_DRAW);
 for(const [name,offset] of [["iOrigin",0],["iBx",12],["iBy",24],["iBz",36]])
  attrib(name,3,48,offset,1);
 gl.bindVertexArray(null);
 return e;
}
function batchGroupIndices(model){
 const parts=new Map();
 const ids=model.triangle_material_ids||[];
 for(let t=0;t<model.indices.length/3;t++){
  const slot=ids[t]||0;
  if(!parts.has(slot))parts.set(slot,[]);
  parts.get(slot).push(...model.indices.slice(3*t,3*t+3));
 }
 const combined=new Uint32Array(model.indices.length);
 const groups=[];let pos=0;
 for(const [slot,indices] of parts){
  combined.set(indices,pos);
  groups.push({slot,count:indices.length,offsetBytes:pos*4});
  pos+=indices.length;
 }
 return {indices:combined,groups};
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
    entry.model=name;
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
  "Original model geometry loaded; separate optional provisional texture folder supported.";
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
function batchValidateTextureManifest(data){
 if(!data||data.format!=="lfd2-original-hotel-provisional-model-textures-v1"||
    !Array.isArray(data.models)||data.models.length>100000)
    throw Error("Expected privately converted original model texture-manifest.json");
 const unique=new Set();
 for(const item of data.models){
  if(!item||typeof item.model!=="string"||
     !/^models\/[a-z0-9_./-]+\.mdl$/.test(item.model)||
     !Number.isInteger(item.slot)||item.slot<0||item.slot>1024||
     item.mapping!=="PROVISIONAL_EXACT_FILENAME_NOT_VMT_VERIFIED"||
     typeof item.png!=="string"||
     !/^textures\/[a-z0-9_.\/-]+\.png$/.test(item.png)||
     item.png.split("/").includes("..")||
     unique.has(item.model+"#"+item.slot))
     throw Error("Invalid or duplicate original provisional material assignment");
  unique.add(item.model+"#"+item.slot);
 }
 return data.models;
}
async function batchLoadTextureFolder(filelist){
 if(!batchEntries.length)
   throw Error("Load original hotel-auto-props-v2 model folder first.");
 const files=Array.from(filelist||[]);
 if(files.length<2||files.length>25000)
   throw Error("Select original hotel-model-textures folder, including its manifest.");
 const byPath=new Map();
 for(const file of files){
  const raw=(file.webkitRelativePath||"").replace(/\\/g,"/");
  const root=raw.split("/")[0],name=raw.slice(root.length+1);
  if(name&&file.size<=40*1024*1024)byPath.set(name,file);
 }
 const mf=byPath.get("texture-manifest.json");
 if(!mf)throw Error("Selected folder lacks original texture-manifest.json");
 const bindings=batchValidateTextureManifest(JSON.parse(await mf.text()));
 let selectedBytes=0;
 const needed=new Map(),owned=new Map(batchEntries.map(e=>[e.model,e]));
 for(const b of bindings){
  if(!owned.has(b.model))continue;
  const file=byPath.get(b.png);
  if(!file)continue;
  if(!needed.has(b.png)){
   needed.set(b.png,file);
   selectedBytes+=file.size;
  }
 }
 if(selectedBytes>BATCH_TEXTURE_MAX_BYTES)
   throw Error("Too many original model PNG texture bytes for safe GPU upload.");
 // A second folder import must free its previous GPU textures first.
 for(const tex of batchTextureCache.values())gl.deleteTexture(tex);
 batchTextureCache.clear();
 for(const e of batchEntries)e.materialTextures.clear();
 let converted=0,skipped=0,totalPixels=0;
 try{
  for(const [path,file] of needed){
   const image=await createImageBitmap(file);
   try{
    if(!image.width||!image.height||image.width>8192||image.height>8192)
     throw Error("Original texture dimensions unsupported");
    // Bound expanded RGBA GPU memory instead of trusting PNG byte sizes.
    if(totalPixels+image.width*image.height>60*1024*1024){
     skipped++;continue;
    }
    totalPixels+=image.width*image.height;
    const tex=gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D,tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.generateMipmap(gl.TEXTURE_2D);
    batchTextureCache.set(path,tex);
    converted++;
   }finally{image.close();}
  }
 }catch(error){
  if(batchTextureStatus)batchTextureStatus.textContent=
     "Partial provisional model textures loaded; error: "+error.message;
  throw error;
 }finally{
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);
  gl.bindTexture(gl.TEXTURE_2D,null);
 }
 let slots=0;
 for(const b of bindings){
  const owner=owned.get(b.model),tex=batchTextureCache.get(b.png);
  if(!owner||!tex){skipped++;continue;}
  if(owner.groups.some(g=>g.slot===b.slot)){
   owner.materialTextures.set(b.slot,tex);slots++;
  }else skipped++;
 }
 if(batchTextureStatus)batchTextureStatus.textContent=
  "Loaded "+converted+" authentic original VTFX PNGs as PROVISIONAL diffuse previews "+
  "for "+slots+" model material slots; "+skipped+" unavailable mappings. "+
  "Binary Xbox VMT shader assignments NOT YET VERIFIED. No map or game files uploaded.";
}
if(batchTextureFolderInput)batchTextureFolderInput.addEventListener("change",async()=>{
 try{
  if(batchTextureStatus)batchTextureStatus.textContent="Importing local original Xbox model image previews...";
  await batchLoadTextureFolder(batchTextureFolderInput.files);
 }catch(error){
  if(batchTextureStatus)batchTextureStatus.textContent="Texture folder stopped: "+error.message;
 }
 batchTextureFolderInput.value="";
});
function renderOriginalHotelBatch(){
 if(!batchProgram||!batchEntries.length||!gl)return;
 gl.useProgram(batchProgram);
 gl.uniform3f(batchUniform.camera,cam.x,cam.y,cam.z);
 gl.uniform1f(batchUniform.yaw,cam.yaw);
 gl.uniform1f(batchUniform.pitch,cam.pitch);
 gl.uniform1f(batchUniform.aspect,cvs.width/cvs.height);
 gl.uniform1i(batchUniform.sampler,0);
 gl.activeTexture(gl.TEXTURE0);
 for(const item of batchEntries){
  gl.uniform3fv(batchUniform.color,item.color);
  gl.bindVertexArray(item.vao);
  for(const group of item.groups){
   const tex=item.materialTextures.get(group.slot);
   gl.uniform1i(batchUniform.textured,tex?1:0);
   gl.bindTexture(gl.TEXTURE_2D,tex||null);
   gl.drawElementsInstanced(gl.TRIANGLES,group.count,
                            gl.UNSIGNED_INT,group.offsetBytes,item.placed);
  }
 }
 gl.bindTexture(gl.TEXTURE_2D,null);
 gl.bindVertexArray(null);
 gl.useProgram(program);
}
