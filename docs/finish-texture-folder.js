"use strict";
/* One-folder original hotel texture loader.
   The user explicitly selects research/local/hotel-complete via Chrome's
   directory picker. Reads private texture-manifest.json + PNG File objects,
   never fetches or uploads data. No network or game assets in this repo. */
const finishFolder=document.getElementById("finishFolder");
const finishProgress=document.getElementById("finishProgress");
let finishBusy=false;

function finishNormalizedPath(value) {
 if(typeof value!=="string"||value.length>360||value.startsWith("/")||
    value.includes("\\")||value.split("/").some(x=>x===".."||x==="."||!x))
  return null;
 return value.toLowerCase();
}
function finishMaterialMap(mesh) {
 const result=new Map();
 for(let i=0;i<mesh.materials.length;i++)
  result.set(String(mesh.materials[i]).toLowerCase().replace(/\\/g,"/"),i);
 return result;
}
function finishPlanFiles(files,manifest,mesh) {
 if(!manifest||manifest.format!=="lfd2-private-texture-manifest-v1"||
    !manifest.materials||typeof manifest.materials!=="object"||
    Array.isArray(manifest.materials))
  throw Error("Unsupported private texture manifest");
 const pathIndex=new Map();
 for(const file of files) {
  const raw=(file.webkitRelativePath||file.name).replace(/\\/g,"/");
  const slash=raw.indexOf("/");
  const relative=slash>=0?raw.slice(slash+1):raw;
  const key=finishNormalizedPath(relative);
  if(key && !pathIndex.has(key))pathIndex.set(key,file);
 }
 const materialIds=finishMaterialMap(mesh),work=[];
 const missing=[];
 for(const [original,relative] of Object.entries(manifest.materials)) {
  const material=original.toLowerCase().replace(/\\/g,"/");
  const materialId=materialIds.get(material);
  const imagePath=finishNormalizedPath(relative);
  if(materialId===undefined||!imagePath||!imagePath.startsWith("textures/")||
     !imagePath.endsWith(".png"))continue;
  const file=pathIndex.get(imagePath);
  if(!file||file.size>MM_MAX_PNG_BYTES){missing.push(original);continue;}
  work.push({materialId,original,file,imagePath});
 }
 if(work.length>256)throw Error("Too many original material bindings in manifest");
 return {work,missing};
}
async function loadCompleteTextureFolder(files) {
 if(finishBusy)return;
 if(!mmMesh) {
  finishProgress.textContent="Load c1m1_hotel_spawns_uv.mesh.json first.";
  return;
 }
 const items=Array.from(files||[]);
 const manifestFile=items.find(file=>file.name==="texture-manifest.json");
 if(!manifestFile) {
  finishProgress.textContent="Select the hotel-complete folder containing texture-manifest.json.";
  return;
 }
 if(manifestFile.size>512*1024) {
  finishProgress.textContent="Manifest is larger than supported 512 KB.";return;
 }
 finishBusy=true;
 let count=0,already=0,failed=0;
 try{
  const manifest=JSON.parse(await manifestFile.text());
  const plan=finishPlanFiles(items,manifest,mmMesh);
  finishProgress.textContent="Found "+plan.work.length+
   " material bindings. Loading local images into Chrome...";
  for(const row of plan.work){
   if(mmTextures.has(row.materialId)){already++;continue;}
   if(mmTextures.size>=MM_MAX_TOTAL){
    failed++;continue;
   }
   let image=null;
   try{
    image=await createImageBitmap(row.file);
    if(image.width>4096||image.height>4096)
      throw Error("PNG exceeds 4096px");
    const pixels=image.width*image.height;
    if(mmPixels+pixels>MM_MAX_TOTAL_PIXELS)
      throw Error("Texture memory limit reached");
    const entry=mmInitEntry(row.materialId,image);
    mmTextures.set(row.materialId,entry);
    mmPixels+=entry.pixels;
    count++;
   }catch(error){failed++;}
   finally{if(image)image.close();}
   if((count+failed)%8===0)
    finishProgress.textContent="Loading "+(count+already+failed)+
     "/"+plan.work.length+" materials...";
  }
  mmEnabled=true;mmToggle.textContent="MULTI-TEXTURES ON";
  const triangles=[...mmTextures.values()].reduce((n,item)=>n+item.count/3,0);
  finishProgress.textContent=mmTextures.size+" original materials rendered / "+
   triangles.toLocaleString()+" textured triangles. "+
   count+" newly loaded; "+already+" already present; "+
   (failed+plan.missing.length)+" unavailable. "+
   "See MATERIAL COVERAGE below for untextured surfaces.";
  mmStatus.textContent=finishProgress.textContent;
  if(typeof updateMaterialCoverage==="function")updateMaterialCoverage();
 }catch(error){
  finishProgress.textContent="Texture folder load stopped: "+error.message;
 }finally{
  finishBusy=false;
  if(finishFolder)finishFolder.value="";
 }
}
if(finishFolder)finishFolder.addEventListener("change",()=>{
 loadCompleteTextureFolder(finishFolder.files);
});
