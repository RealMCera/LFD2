"use strict";
/* One authentic original Xbox hotel chair mesh at its actual Source positions.
   Both inputs are user-picked private JSON files. No automatic URL fetch,
   uploads, invented geometry, or bundled commercial game assets.
   This prototype shades true MDL/VVD/VTX triangles in neutral gray until
   original chair materials are decoded. */
const originalChairInput=document.getElementById("originalChairMesh");
const originalPlacementsInput=document.getElementById("originalPropPlacements");
const originalPropStatus=document.getElementById("originalPropStatus");
const originalPropToggle=document.getElementById("originalPropToggle");
const originalNextChair=document.getElementById("originalNextChair");
let originalChairMesh=null,originalPropPlacementData=null;
let originalChairInstances=[],originalChairCursor=-1;
let originalPropProgram=null,originalPropVao=null,originalPropBuffer=null;
let originalPropUniforms=null,originalPropVertexCount=0,originalPropsEnabled=true;

function originalPropsClear(){
 if(gl&&originalPropBuffer)gl.deleteBuffer(originalPropBuffer);
 if(gl&&originalPropVao)gl.deleteVertexArray(originalPropVao);
 originalPropBuffer=originalPropVao=null;originalPropVertexCount=0;
}
function originalPropsReset(){
 originalPropsClear();
 originalChairMesh=null;originalPropPlacementData=null;
 originalChairInstances=[];originalChairCursor=-1;
 if(originalNextChair)originalNextChair.disabled=true;
 if(originalPropStatus)originalPropStatus.textContent=
  "Load private hotel-chair.mesh.json and hotel-all-props.json from research/local to see actual original Source model triangles.";
}
function originalChairValidate(data){
 if(!data||data.format!=="lfd2-source-original-model-v1"||
    data.model!=="models/props_furniture/hotel_chair.mdl"||
    !Array.isArray(data.vertices)||!Array.isArray(data.indices)||
    !Array.isArray(data.normals)||data.vertices.length>300000||
    data.indices.length>600000||data.indices.length%3!==0||
    data.vertices.length%3!==0||
    data.normals.length!==data.vertices.length)
   throw Error("Expected privately converted original hotel_chair.mesh.json");
 const count=data.vertices.length/3;
 if(count<3||data.indices.length<3||
    !data.vertices.every(n=>Number.isFinite(n)&&Math.abs(n)<1e6)||
    !data.normals.every(n=>Number.isFinite(n)&&Math.abs(n)<100)||
    !data.indices.every(n=>Number.isInteger(n)&&n>=0&&n<count))
   throw Error("Original chair vertices or indices failed validation");
 return data;
}
function originalPlacementValidate(data){
 if(!data||data.format!=="lfd2-original-prop-placements-v1"||
    !Array.isArray(data.placements)||data.placements.length>100000)
   throw Error("Load the private research/local/hotel-all-props.json manifest");
 const chair=data.placements.filter(p=>p&&
    p.model==="models/props_furniture/hotel_chair.mdl"&&
    Array.isArray(p.origin)&&p.origin.length===3&&
    Array.isArray(p.angles)&&p.angles.length===3&&
    [...p.origin,...p.angles].every(n=>Number.isFinite(n)&&Math.abs(n)<1e6)
   );
 if(chair.length<1||chair.length>1000)
   throw Error("No valid authored original hotel chair placements found");
 return chair;
}
function originalRotate(point,angles){
 // Source AngleVectors: model X forward, Y left, Z up; degrees in BSP.
 const rad=Math.PI/180;
 const [pitch,yaw,roll]=angles.map(a=>a*rad);
 const sp=Math.sin(pitch),cp=Math.cos(pitch),
       sy=Math.sin(yaw),cy=Math.cos(yaw),
       sr=Math.sin(roll),cr=Math.cos(roll);
 const f=[cp*cy,cp*sy,-sp];
 const r=[-sr*sp*cy+cr*sy,-sr*sp*sy-cr*cy,-sr*cp];
 const u=[cr*sp*cy+sr*sy,cr*sp*sy-sr*cy,cr*cp];
 return [0,1,2].map(i=>point[0]*f[i]-point[1]*r[i]+point[2]*u[i]);
}
function originalChairPacked(meshData,placements){
 const perInstance=meshData.indices.length;
 if(perInstance*placements.length>750000)
  throw Error("Too many triangles for bounded original-chair preview");
 const packed=new Float32Array(perInstance*placements.length*6);
 let offset=0;
 for(const p of placements){
  for(const vertex of meshData.indices){
   const local=3*vertex;
   const xyz=originalRotate(meshData.vertices.slice(local,local+3),p.angles);
   const n=originalRotate(meshData.normals.slice(local,local+3),p.angles);
   packed[offset++]=xyz[0]+p.origin[0];
   packed[offset++]=xyz[1]+p.origin[1];
   packed[offset++]=xyz[2]+p.origin[2];
   packed[offset++]=n[0];packed[offset++]=n[1];packed[offset++]=n[2];
  }
 }
 return packed;
}
function originalPropsInitGL(){
 if(originalPropProgram)return;
 if(!gl)throw Error("WebGL2 required");
 const vs=shader(gl.VERTEX_SHADER,[
 "#version 300 es","precision highp float;",
 "in vec3 aPos,aNormal;",
 "uniform vec3 uCamera;","uniform float uYaw,uPitch,uAspect;",
 "out float vLight;",
 "void main(){",
 "vec3 forward=vec3(cos(uYaw)*cos(uPitch),sin(uYaw)*cos(uPitch),sin(uPitch));",
 "vec3 right=vec3(-sin(uYaw),cos(uYaw),0.0);",
 "vec3 up=cross(forward,right);",
 "vec3 delta=aPos-uCamera;",
 "vec3 eye=vec3(dot(delta,right),dot(delta,up),dot(delta,forward));",
 "float nearP=2.0,farP=25000.0;",
 "float z=eye.z*(farP+nearP)/(farP-nearP)-(2.0*farP*nearP)/(farP-nearP);",
 "gl_Position=vec4(eye.x*1.35/uAspect,eye.y*1.35,z,eye.z);",
 "vLight=0.30+0.70*max(0.0,dot(normalize(aNormal),normalize(vec3(.4,-.2,.9))));",
 "}"
 ].join("\n"));
 const fs=shader(gl.FRAGMENT_SHADER,[
 "#version 300 es","precision highp float;","in float vLight;",
 "out vec4 outColor;",
 "void main(){outColor=vec4(vec3(.67,.76,.78)*vLight,1.0);}"
 ].join("\n"));
 const prog=gl.createProgram();gl.attachShader(prog,vs);gl.attachShader(prog,fs);
 gl.linkProgram(prog);
 if(!gl.getProgramParameter(prog,gl.LINK_STATUS))
   throw Error("Original prop shader: "+gl.getProgramInfoLog(prog));
 gl.deleteShader(vs);gl.deleteShader(fs);originalPropProgram=prog;
 originalPropUniforms={
  camera:gl.getUniformLocation(prog,"uCamera"),
  yaw:gl.getUniformLocation(prog,"uYaw"),
  pitch:gl.getUniformLocation(prog,"uPitch"),
  aspect:gl.getUniformLocation(prog,"uAspect")
 };
}
function originalChairCamera(placement){
 // Source props orient model X forward, Y left, Z up.
 // View from 120 Source units in front of the original model,
 // 56 units above its authored origin. Camera looks back at the chair.
 const yaw=placement.angles[1]*Math.PI/180;
 return {
  x:placement.origin[0]+Math.cos(yaw)*120,
  y:placement.origin[1]+Math.sin(yaw)*120,
  z:placement.origin[2]+56,
  yaw:yaw+Math.PI,
  pitch:-0.20
 };
}
function originalJumpToChair(){
 if(!mesh||!originalChairMesh||!originalChairInstances.length)return;
 originalChairCursor=(originalChairCursor+1)%originalChairInstances.length;
 Object.assign(cam,originalChairCamera(originalChairInstances[originalChairCursor]));
 if(typeof loader!=="undefined"&&loader)loader.style.display="none";
 if(typeof show!=="undefined"&&show)show.style.display="block";
 if(typeof flashHint==="function")
  flashHint("ORIGINAL CHAIR "+(originalChairCursor+1)+"/"+originalChairInstances.length+
            " · 1,403 AUTHENTIC SOURCE TRIANGLES PER CHAIR · C FOR NEXT");
}
if(originalNextChair)originalNextChair.addEventListener("click",originalJumpToChair);

function rebuildOriginalProps(){
 originalPropsClear();
 if(!originalChairMesh||!originalPropPlacementData)return;
 const instances=originalPlacementValidate(originalPropPlacementData);
 const packed=originalChairPacked(originalChairMesh,instances);
 originalChairInstances=instances;
 originalChairCursor=-1;
 originalPropsInitGL();
 originalPropVao=gl.createVertexArray();
 originalPropBuffer=gl.createBuffer();
 gl.bindVertexArray(originalPropVao);
 gl.bindBuffer(gl.ARRAY_BUFFER,originalPropBuffer);
 gl.bufferData(gl.ARRAY_BUFFER,packed,gl.STATIC_DRAW);
 for(const [name,offset] of [["aPos",0],["aNormal",12]]){
  const loc=gl.getAttribLocation(originalPropProgram,name);
  if(loc<0)throw Error("Original prop shader missing "+name);
  gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,24,offset);
 }
 gl.bindVertexArray(null);
 originalPropVertexCount=packed.length/6;
 if(originalNextChair)originalNextChair.disabled=false;
 originalPropStatus.textContent=instances.length+" AUTHENTIC CHAIR PLACEMENTS · "+
   originalChairMesh.indices.length/3+" original triangles each · "+
   (originalPropVertexCount/3).toLocaleString()+
   " original-model overlay triangles in neutral diagnostic shading. "+
   "Original chair skin/lighting not yet converted.";
}
async function originalPropLoadFile(file,kind){
 if(!file||file.size>36*1024*1024)
   throw Error("Private JSON file is missing or exceeds 36 MB limit");
 const data=JSON.parse(await file.text());
 if(kind==="mesh")originalChairMesh=originalChairValidate(data);
 else{originalPlacementValidate(data);originalPropPlacementData=data;}
 rebuildOriginalProps();
 if(!originalChairMesh||!originalPropPlacementData)
  originalPropStatus.textContent="Loaded "+kind+". Select the other local JSON file.";
}
if(originalChairInput)originalChairInput.addEventListener("change",async()=>{
 try{await originalPropLoadFile(originalChairInput.files[0],"mesh");}
 catch(err){originalPropsClear();originalPropStatus.textContent=err.message;}
 originalChairInput.value="";
});
if(originalPlacementsInput)originalPlacementsInput.addEventListener("change",async()=>{
 try{await originalPropLoadFile(originalPlacementsInput.files[0],"placements");}
 catch(err){originalPropsClear();originalPropStatus.textContent=err.message;}
 originalPlacementsInput.value="";
});
if(originalPropToggle)originalPropToggle.addEventListener("click",()=>{
 originalPropsEnabled=!originalPropsEnabled;
 originalPropToggle.textContent=originalPropsEnabled?"HIDE ORIGINAL CHAIRS":"SHOW ORIGINAL CHAIRS";
});
function renderOriginalHotelProps(){
 if(!originalPropsEnabled||!originalPropVertexCount||!originalPropProgram||!gl)return;
 gl.useProgram(originalPropProgram);gl.bindVertexArray(originalPropVao);
 gl.uniform3f(originalPropUniforms.camera,cam.x,cam.y,cam.z);
 gl.uniform1f(originalPropUniforms.yaw,cam.yaw);
 gl.uniform1f(originalPropUniforms.pitch,cam.pitch);
 gl.uniform1f(originalPropUniforms.aspect,cvs.width/cvs.height);
 gl.drawArrays(gl.TRIANGLES,0,originalPropVertexCount);
 gl.bindVertexArray(null);gl.useProgram(program);
}
