"use strict";
/* Optional Source texture preview. No network calls or bundled game images.
   This classic script loads after the geometry viewer's original script. */
const mpPanel=document.getElementById("materialPanel");
const mpSelect=document.getElementById("materialSelect");
const mpFile=document.getElementById("textureFile");
const mpStatus=document.getElementById("textureStatus");
const mpToggle=document.getElementById("textureToggle");
let mpData=null,mpProgram=null,mpVAO=null,mpBuffer=null,mpTexture=null;
let mpUniform={},mpVertexCount=0,mpTextureLoaded=false,mpVisible=true,mpTextureName="";
const mpVertexShader=[
"#version 300 es",
"precision highp float;",
"in vec3 aPos;",
"in vec2 aUV;",
"uniform vec3 uCamera;",
"uniform float uYaw,uPitch,uAspect;",
"out vec2 vUV;",
"void main(){",
"vec3 forward=vec3(cos(uYaw)*cos(uPitch),sin(uYaw)*cos(uPitch),sin(uPitch));",
"vec3 right=vec3(-sin(uYaw),cos(uYaw),0.0);",
"vec3 up=cross(forward,right);",
"vec3 delta=aPos-uCamera;",
"vec3 eye=vec3(dot(delta,right),dot(delta,up),dot(delta,forward));",
"float nearP=2.0,farP=25000.0;",
"float z=eye.z*(farP+nearP)/(farP-nearP)-(2.0*farP*nearP)/(farP-nearP);",
"gl_Position=vec4(eye.x*1.35/uAspect,eye.y*1.35,z,eye.z);",
"vUV=aUV;",
"}"
].join("\n");
const mpFragmentShader=[
"#version 300 es","precision highp float;","in vec2 vUV;",
"uniform sampler2D uSampler;","out vec4 outColor;",
"void main(){outColor=texture(uSampler,vUV);}"
].join("\n");

function mpInitGL(){
 if(mpProgram||!gl)return;
 const vs=shader(gl.VERTEX_SHADER,mpVertexShader);
 const fs=shader(gl.FRAGMENT_SHADER,mpFragmentShader);
 const prog=gl.createProgram();
 gl.attachShader(prog,vs);gl.attachShader(prog,fs);gl.linkProgram(prog);
 if(!gl.getProgramParameter(prog,gl.LINK_STATUS))
   throw Error(gl.getProgramInfoLog(prog));
 gl.deleteShader(vs);gl.deleteShader(fs);mpProgram=prog;
 mpVAO=gl.createVertexArray();mpBuffer=gl.createBuffer();mpTexture=gl.createTexture();
 gl.bindVertexArray(mpVAO);gl.bindBuffer(gl.ARRAY_BUFFER,mpBuffer);
 const loc=gl.getAttribLocation(prog,"aPos"),uvloc=gl.getAttribLocation(prog,"aUV");
 gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,20,0);
 gl.enableVertexAttribArray(uvloc);gl.vertexAttribPointer(uvloc,2,gl.FLOAT,false,20,12);
 gl.bindVertexArray(null);
 mpUniform={
  camera:gl.getUniformLocation(prog,"uCamera"),
  yaw:gl.getUniformLocation(prog,"uYaw"),
  pitch:gl.getUniformLocation(prog,"uPitch"),
  aspect:gl.getUniformLocation(prog,"uAspect"),
  sampler:gl.getUniformLocation(prog,"uSampler")
 };
}

function mpValidate(data){
 if(data.uv_format!=="source-face-corners-1"||
    !Array.isArray(data.materials)||
    !Array.isArray(data.corner_uvs)||
    !Array.isArray(data.triangle_material_ids))return false;
 if(data.corner_uvs.length!==data.indices.length*2||
    data.triangle_material_ids.length!==data.indices.length/3||
    data.materials.length>10000)throw Error("Inconsistent UV/material array lengths");
 for(const uv of data.corner_uvs)
  if(!Number.isFinite(uv)||Math.abs(uv)>1e7)throw Error("Invalid texture coordinates");
 for(const id of data.triangle_material_ids)
  if(!Number.isInteger(id)||id<0||id>=data.materials.length)
   throw Error("Invalid triangle material index");
 return true;
}
function mpBuildPreview(){
 mpVertexCount=0;
 if(!mpData||!mpProgram)return;
 const chosen=Number(mpSelect.value);
 if(!Number.isInteger(chosen)||chosen<0||chosen>=mpData.materials.length)return;
 const data=mpData,pos=data.vertices,idx=data.indices,uv=data.corner_uvs,mat=data.triangle_material_ids;
 const packed=[];
 for(let t=0;t<mat.length;t++){
  if(mat[t]!==chosen)continue;
  for(let c=0;c<3;c++){
   const ix=idx[3*t+c]*3,u=(3*t+c)*2;
   packed.push(pos[ix],pos[ix+1],pos[ix+2],uv[u],uv[u+1]);
  }
 }
 gl.bindBuffer(gl.ARRAY_BUFFER,mpBuffer);
 gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(packed),gl.STATIC_DRAW);
 mpVertexCount=packed.length/5;
 mpStatus.textContent=(mpVertexCount/3).toLocaleString()+" triangles use "+data.materials[chosen]+
  (mpTextureLoaded?" · PNG: "+mpTextureName:" · select a matching PNG");
}
function setUvData(data){
 mpData=null;mpVertexCount=0;mpTextureLoaded=false;mpTextureName="";
 mpPanel.style.display="none";mpFile.value="";
 try{
  if(!mpValidate(data))return;
  mpInitGL();mpData=data;mpPanel.style.display="block";mpSelect.replaceChildren();
  for(let i=0;i<data.materials.length;i++){
   const option=document.createElement("option");
   option.value=String(i);option.textContent=data.materials[i];
   mpSelect.appendChild(option);
  }
  const start=data.materials.findIndex(s=>s.toLowerCase()==="plaster/plaster_int_14");
  mpSelect.value=String(start>=0?start:0);mpBuildPreview();
 }catch(error){
  mpData=null;mpPanel.style.display="block";
  mpStatus.textContent="UV preview unavailable: "+error.message;
 }
}
mpSelect.addEventListener("change",()=>{
 mpTextureLoaded=false;mpTextureName="";mpFile.value="";mpBuildPreview();
 if(typeof updateMaterialCoverage==="function")updateMaterialCoverage();
});
mpFile.addEventListener("change",async()=>{
 const file=mpFile.files&&mpFile.files[0];
 if(!file||!mpData||!mpProgram)return;
 if(file.size>40*1024*1024){mpStatus.textContent="PNG file exceeds 40 MB limit.";return;}
 try{
  const bmp=await createImageBitmap(file);
  if(bmp.width>4096||bmp.height>4096){
   bmp.close();throw Error("PNG is larger than 4096px");
  }
  gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,mpTexture);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,bmp);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.generateMipmap(gl.TEXTURE_2D);
  bmp.close();mpTextureLoaded=true;mpVisible=true;mpTextureName=file.name;
  mpToggle.textContent="TEXTURE PREVIEW ON";mpBuildPreview();
  if(typeof updateMaterialCoverage==="function")updateMaterialCoverage();
  flashHint("REAL TEXTURE PREVIEW · OPEN MAP LOADER TO SWITCH MATERIAL OR PNG");
 }catch(error){mpTextureLoaded=false;mpStatus.textContent="Cannot load PNG: "+error.message;}
});
mpToggle.addEventListener("click",()=>{
 mpVisible=!mpVisible;
 mpToggle.textContent=mpVisible?"TEXTURE PREVIEW ON":"TEXTURE PREVIEW OFF";
 if(typeof updateMaterialCoverage==="function")updateMaterialCoverage();
});
function renderMaterialPreview(){
 if(!mpTextureLoaded||!mpVisible||!mpVertexCount||!mpProgram)return;
 gl.useProgram(mpProgram);gl.bindVertexArray(mpVAO);
 gl.uniform3f(mpUniform.camera,cam.x,cam.y,cam.z);
 gl.uniform1f(mpUniform.yaw,cam.yaw);
 gl.uniform1f(mpUniform.pitch,cam.pitch);
 gl.uniform1f(mpUniform.aspect,cvs.width/cvs.height);
 gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,mpTexture);
 gl.uniform1i(mpUniform.sampler,0);
 gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(-1,-1);
 gl.drawArrays(gl.TRIANGLES,0,mpVertexCount);
 gl.disable(gl.POLYGON_OFFSET_FILL);
 gl.bindVertexArray(null);gl.useProgram(program);
}