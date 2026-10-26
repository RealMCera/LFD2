"use strict";
/* Material coverage diagnostic for the user's private original Source brush mesh.
   Reads only loaded mesh metadata and local PNG state: no network/filesystem. */
const coverageSummary=document.getElementById("coverageSummary");
const coverageMissing=document.getElementById("coverageMissing");
const coverageRefresh=document.getElementById("coverageRefresh");
const coverageBar=document.getElementById("coverageBar");

function classifySourceMaterial(name) {
 const value=String(name||"").toLowerCase().replace(/\\/g,"/");
 if(value.startsWith("tools/")||value.startsWith("dev/"))
  return "tool/debug";
 if(value.startsWith("sky/")||value.startsWith("effects/"))
  return "sky/effect";
 return "surface-candidate";
}
function coverageByMaterial(mesh,loadedIds){
 if(!mesh||!Array.isArray(mesh.triangle_material_ids)||
    !Array.isArray(mesh.materials))return null;
 const totals=new Uint32Array(mesh.materials.length);
 for(const id of mesh.triangle_material_ids){
  if(Number.isInteger(id)&&id>=0&&id<totals.length)totals[id]++;
 }
 const total=mesh.triangle_material_ids.length;
 let textured=0,loadedCount=0;
 const missing=[];
 let unknownTool=0,unknownSurface=0;
 for(let i=0;i<totals.length;i++){
  const tri=totals[i],name=mesh.materials[i],kind=classifySourceMaterial(name);
  if(loadedIds.has(i)){textured+=tri;loadedCount++;}
  else{
   missing.push({name,tri,kind,id:i});
   if(kind==="tool/debug"||kind==="sky/effect")unknownTool+=tri;
   else unknownSurface+=tri;
  }
 }
 missing.sort((a,b)=>b.tri-a.tri||a.name.localeCompare(b.name));
 return {total,textured,loadedCount,unknownTool,unknownSurface,missing,
         fraction:total?textured/total:0};
}
function updateMaterialCoverage(){
 if(!coverageSummary||!coverageMissing)return;
 const data=(typeof mmMesh!=="undefined"&&mmMesh)
   ||(typeof mpData!=="undefined"&&mpData);
 if(!data){
  coverageSummary.textContent="Load the UV-enriched hotel mesh to inspect coverage.";
  coverageMissing.textContent="";
  if(coverageBar)coverageBar.style.width="0%";
  return;
 }
 const loaded=new Set();
 if(typeof mmEnabled!=="undefined"&&mmEnabled&&typeof mmTextures!=="undefined")
  for(const id of mmTextures.keys())loaded.add(id);
 if(typeof mpTextureLoaded!=="undefined"&&mpTextureLoaded&&mpVisible){
  const selected=Number(mpSelect.value);
  if(Number.isInteger(selected))loaded.add(selected);
 }
 const report=coverageByMaterial(data,loaded);
 const format=n=>n.toLocaleString();
 coverageSummary.textContent=
  format(report.textured)+" / "+format(report.total)+" brush triangles textured ("+
  (100*report.fraction).toFixed(1)+"%) · "+report.loadedCount+
  " material IDs loaded\n"+
  format(report.unknownSurface)+" untextured surface-candidate triangles · "+
  format(report.unknownTool)+" tool/debug/sky/effect triangles";
 if(coverageBar)coverageBar.style.width=(100*report.fraction).toFixed(1)+"%";
 const top=report.missing.slice(0,14);
 const lines=top.map(row=>format(row.tri).padStart(6," ")+
  " tri  "+row.name+(row.kind!=="surface-candidate"?" ["+row.kind+"]":""));
 coverageMissing.textContent=
  "TOP MATERIAL IDs WITHOUT AN ACTIVE PNG:\n"+
  (lines.length?lines.join("\n"):"All triangle materials covered.")+
  "\n\nTool/debug/sky labels are diagnostic, not proof of what should be visible.";
}
if(coverageRefresh)coverageRefresh.addEventListener("click",updateMaterialCoverage);
