"use strict";
/* Preview multiple locally selected PNGs using Source per-corner UVs.
   No remote fetches, bundled game assets, or writes to local disk. */
const mmFile=document.getElementById("multiTextureFiles");
const mmStatus=document.getElementById("multiTextureStatus");
const mmToggle=document.getElementById("multiTextureToggle");
let mmMesh=null,mmTextures=new Map(),mmEnabled=true;
const MM_MAX_FILES=16,MM_MAX_TOTAL=48,MM_MAX_PNG_BYTES=40*1024*1024;
const MM_MAX_TOTAL_PIXELS=24*1024*1024;
let mmPixels=0;

function materialBasename(name) {
 return String(name).replace(/\\/g,"/").toLowerCase().split("/").pop();
}
function pngBasename(filename) {
 return String(filename).toLowerCase().replace(/\.png$/i,"")
           .replace(/(?:\.360)?_resource_\d+$/i,"")
           .replace(/(?:\.360)?_frame_\d+$/i,"")
           .replace(/\.360$/i,"");
}
function matchingMaterialIndex(filename, materials) {
 const base=pngBasename(filename),ids=[];
 for(let i=0;i<materials.length;i++)
  if(materialBasename(materials[i])===base)ids.push(i);
 return ids.length===1?ids[0]:-1;
}
function mmClear(){
 for(const item of mmTextures.values()){
  gl.deleteVertexArray(item.vao);gl.deleteBuffer(item.buffer);gl.deleteTexture(item.texture);
 }
 mmTextures.clear();mmPixels=0;
 if(mmFile)mmFile.value="";
}
function setMultiUvData(data){
 mmClear();
 mmMesh=(data&&data.uv_format==="source-face-corners-1"&&
         Array.isArray(data.corner_uvs)&&Array.isArray(data.triangle_material_ids))
        ?data:null;
 if(mmStatus)mmStatus.textContent=mmMesh?
 "Select up to 16 PNGs per round, up to 48 total. Already loaded PNGs can be reselected safely.":
 "Load the UV-enriched mesh for multi-material preview.";
}
function mmGeometry(data,materialId){
 const packed=[];
 for(let t=0;t<data.triangle_material_ids.length;t++){
  if(data.triangle_material_ids[t]!==materialId)continue;
  for(let c=0;c<3;c++){
   const vi=data.indices[t*3+c]*3,ui=(t*3+c)*2;
   packed.push(data.vertices[vi],data.vertices[vi+1],data.vertices[vi+2],
               data.corner_uvs[ui],data.corner_uvs[ui+1]);
  }
 }
 return new Float32Array(packed);
}
function mmInitEntry(materialId,bitmap){
 mpInitGL();
 const positions=mmGeometry(mmMesh,materialId);
 if(!positions.length)throw Error("Material has no visible triangles");
 const vao=gl.createVertexArray(),buffer=gl.createBuffer(),texture=gl.createTexture();
 gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
 gl.bufferData(gl.ARRAY_BUFFER,positions,gl.STATIC_DRAW);
 const a=gl.getAttribLocation(mpProgram,"aPos"),u=gl.getAttribLocation(mpProgram,"aUV");
 gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,3,gl.FLOAT,false,20,0);
 gl.enableVertexAttribArray(u);gl.vertexAttribPointer(u,2,gl.FLOAT,false,20,12);
 gl.bindVertexArray(null);
 gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);
 gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
 gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,bitmap);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
 gl.generateMipmap(gl.TEXTURE_2D);
 return {vao,buffer,texture,count:positions.length/5,pixels:bitmap.width*bitmap.height};
}
async function loadManyPngs(files){
 if(!mmMesh){mmStatus.textContent="Load the UV-enriched hotel mesh first.";return;}
 if(!files||!files.length)return;
 if(files.length>MM_MAX_FILES){mmStatus.textContent="Choose at most 16 PNGs in one selection.";return;}
 let added=0,duplicates=0,ignored=0;const errors=[];
 for(const file of files){
  if(mmTextures.size>=MM_MAX_TOTAL){ignored++;errors.push("Texture limit of 48 reached");continue;}
  if(!/\.png$/i.test(file.name)||file.size>MM_MAX_PNG_BYTES){ignored++;continue;}
  const id=matchingMaterialIndex(file.name,mmMesh.materials);
  if(id<0){errors.push(file.name+": unmatched or ambiguous");ignored++;continue;}
  if(mmTextures.has(id)){duplicates++;continue;}
  let bitmap=null;
  try{
   bitmap=await createImageBitmap(file);
   if(bitmap.width>4096||bitmap.height>4096)throw Error("PNG exceeds 4096px");
   if(mmPixels+bitmap.width*bitmap.height>MM_MAX_TOTAL_PIXELS)
    throw Error("Private GPU texture pixel budget reached (24M pixels)");
   const entry=mmInitEntry(id,bitmap);
   mmTextures.set(id,entry);mmPixels+=entry.pixels;added++;
  }catch(err){ignored++;errors.push(file.name+": "+err.message);}
  finally{if(bitmap)bitmap.close();}
 }
 const triangles=[...mmTextures.values()].reduce((n,item)=>n+item.count/3,0);
 mmStatus.textContent=mmTextures.size+" materials / "+triangles.toLocaleString()+
 " triangles textured · "+added+" added · "+duplicates+" already loaded · "+ignored+" failed/skipped"+
 (errors.length?"\n"+errors.slice(0,3).join("\n"):"");
 mmEnabled=true;mmToggle.textContent="MULTI-TEXTURES ON";
 if(typeof updateMaterialCoverage==="function")updateMaterialCoverage();
}
if(mmFile)mmFile.addEventListener("change",()=>loadManyPngs(Array.from(mmFile.files||[])));
if(mmToggle)mmToggle.addEventListener("click",()=>{
 mmEnabled=!mmEnabled;mmToggle.textContent=mmEnabled?"MULTI-TEXTURES ON":"MULTI-TEXTURES OFF";
 if(typeof updateMaterialCoverage==="function")updateMaterialCoverage();
});
function renderMultiMaterials(){
 if(!mmEnabled||!mmMesh||!mmTextures.size||!mpProgram)return;
 gl.useProgram(mpProgram);
 gl.uniform3f(mpUniform.camera,cam.x,cam.y,cam.z);
 gl.uniform1f(mpUniform.yaw,cam.yaw);
 gl.uniform1f(mpUniform.pitch,cam.pitch);
 gl.uniform1f(mpUniform.aspect,cvs.width/cvs.height);
 gl.uniform1i(mpUniform.sampler,0);
 gl.activeTexture(gl.TEXTURE0);
 gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(-2,-2);
 for(const item of mmTextures.values()){
  gl.bindVertexArray(item.vao);gl.bindTexture(gl.TEXTURE_2D,item.texture);
  gl.drawArrays(gl.TRIANGLES,0,item.count);
 }
 gl.disable(gl.POLYGON_OFFSET_FILL);
 gl.bindVertexArray(null);gl.useProgram(program);
}
