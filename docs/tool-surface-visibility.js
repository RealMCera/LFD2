"use strict";
/* Optional Source brush diagnostics: non-rendering trigger, fog, clip, sky
   and developer materials should not be drawn as opaque gray walls.
   This only filters WebGL base draw indices, retaining the original private
   mesh, Source UVs, raycast data, triangle counts and viewer controls. */
const hideToolBrushes=document.getElementById("hideToolBrushes");
const hideToolInfo=document.getElementById("hideToolInfo");
let toolSourceMesh=null;
function showOriginalToolSurfaces(data){
 toolSourceMesh=(data&&data.uv_format==="source-face-corners-1"&&
                 Array.isArray(data.triangle_material_ids)&&
                 Array.isArray(data.materials))?data:null;
 updateToolSurfaces();
}
function visibleBrushIndices(meshData, hideTools) {
 const src=meshData.indices;
 if(!hideTools || !Array.isArray(meshData.triangle_material_ids))
  return {indices:src,hidden:0};
 const visible=[];
 let hidden=0;
 for(let i=0;i<meshData.triangle_material_ids.length;i++){
  const name=String(meshData.materials[meshData.triangle_material_ids[i]]||"")
    .toLowerCase().replace(/\\/g,"/");
  // These are Source tool/debug surfaces, not hotel wall/floor art.
  const hide=name.startsWith("tools/")||name.startsWith("dev/")||
             name.startsWith("sky/")||name.startsWith("effects/");
  if(hide)hidden++;
  else visible.push(src[3*i],src[3*i+1],src[3*i+2]);
 }
 return {indices:visible,hidden};
}
function updateToolSurfaces(){
 if(!toolSourceMesh||!gl||!indexBuffer)return;
 const result=visibleBrushIndices(toolSourceMesh,hideToolBrushes.checked);
 const indices=new Uint32Array(result.indices);
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indexBuffer);
 gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);
 indexCount=indices.length;
 const edges=new Uint32Array(indices.length*2);
 for(let i=0,j=0;i<indices.length;i+=3){
  const a=indices[i],b=indices[i+1],c=indices[i+2];
  edges[j++]=a;edges[j++]=b;edges[j++]=b;edges[j++]=c;
  edges[j++]=c;edges[j++]=a;
 }
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,lineIndexBuffer);
 gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,edges,gl.STATIC_DRAW);
 lineCount=edges.length;
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indexBuffer);
 hideToolInfo.textContent=result.hidden.toLocaleString()+
  " nonvisual/debug triangles hidden from gray base layer (toggle to compare).";
}
if(hideToolBrushes)hideToolBrushes.addEventListener("change",updateToolSurfaces);
