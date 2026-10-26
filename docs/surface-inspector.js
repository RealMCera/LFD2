"use strict";
/* Read-only local BSP surface inspector. Press I while aiming at a surface.
   Uses the same original triangle geometry, Source per-face material IDs
   and camera orientation as the WebGL2 viewer. No network requests. */
const inspectStatus = document.getElementById("inspectSurfaceStatus");
const inspectButton = document.getElementById("inspectSurfaceButton");
const inspectUseButton = document.getElementById("inspectUseMaterial");
let inspectLastHit = null;

function intersectRayTriangle(origin, direction, a, b, c) {
 const e1x=b[0]-a[0],e1y=b[1]-a[1],e1z=b[2]-a[2];
 const e2x=c[0]-a[0],e2y=c[1]-a[1],e2z=c[2]-a[2];
 const px=direction[1]*e2z-direction[2]*e2y;
 const py=direction[2]*e2x-direction[0]*e2z;
 const pz=direction[0]*e2y-direction[1]*e2x;
 const det=e1x*px+e1y*py+e1z*pz;
 if(Math.abs(det)<1e-8)return null;
 const inv=1/det;
 const tx=origin[0]-a[0],ty=origin[1]-a[1],tz=origin[2]-a[2];
 const u=(tx*px+ty*py+tz*pz)*inv;
 if(u<0||u>1)return null;
 const qx=ty*e1z-tz*e1y;
 const qy=tz*e1x-tx*e1z;
 const qz=tx*e1y-ty*e1x;
 const v=(direction[0]*qx+direction[1]*qy+direction[2]*qz)*inv;
 if(v<0||u+v>1)return null;
 const distance=(e2x*qx+e2y*qy+e2z*qz)*inv;
 return distance>0.05?distance:null;
}
function raycastSourceMaterial(data, camera, maxDistance=8192) {
 if(!data||!Array.isArray(data.indices)||!Array.isArray(data.triangle_material_ids))return null;
 const d=[Math.cos(camera.yaw)*Math.cos(camera.pitch),
          Math.sin(camera.yaw)*Math.cos(camera.pitch),Math.sin(camera.pitch)];
 const eye=[camera.x,camera.y,camera.z],verts=data.vertices,idx=data.indices;
 let nearest=maxDistance,selected=-1;
 for(let i=0;i<idx.length;i+=3){
  const ia=idx[i]*3,ib=idx[i+1]*3,ic=idx[i+2]*3;
  const a=[verts[ia],verts[ia+1],verts[ia+2]];
  const b=[verts[ib],verts[ib+1],verts[ib+2]];
  const c=[verts[ic],verts[ic+1],verts[ic+2]];
  const distance=intersectRayTriangle(eye,d,a,b,c);
  if(distance!==null&&distance<nearest){nearest=distance;selected=i/3;}
 }
 if(selected<0)return null;
 const matId=data.triangle_material_ids[selected];
 if(!Number.isInteger(matId)||matId<0||matId>=data.materials.length)return null;
 return {material:data.materials[matId],materialId:matId,
         triangle:selected,distance:nearest,
         position:[eye[0]+d[0]*nearest,eye[1]+d[1]*nearest,eye[2]+d[2]*nearest]};
}
function inspectSurface() {
 if(!mpData){inspectStatus.textContent="Select a UV-enriched Source mesh first.";return null;}
 const result=raycastSourceMaterial(mpData,cam);
 inspectLastHit=result;
 if(!result){
  inspectStatus.textContent="No brush triangle under crosshair within 8192 Source units.";
  flashHint("SURFACE INSPECTOR · NO BSP SURFACE HIT");return null;
 }
 const loaded=typeof mmTextures!=="undefined"&&mmTextures.has(result.materialId);
 const info=result.material+" · "+result.distance.toFixed(0)+" units · "+
   "triangle #"+result.triangle+" · "+(loaded?"multi-PNG loaded":"no multi-PNG for this material");
 inspectStatus.textContent=info;
 flashHint("SOURCE MATERIAL: "+result.material+" · PRESS I TO INSPECT");
 return result;
}
if(inspectButton)inspectButton.addEventListener("click",inspectSurface);
if(inspectUseButton)inspectUseButton.addEventListener("click",()=>{
 if(!inspectLastHit||!mpData)return;
 const materialIndex=inspectLastHit.materialId;
 mpSelect.value=String(materialIndex);
 mpSelect.dispatchEvent(new Event("change"));
 inspectStatus.textContent="Selected "+inspectLastHit.material+
 " for the single-material PNG preview. Choose its correctly matched PNG above.";
});
document.addEventListener("keydown",event=>{
 if(event.code!=="KeyI"||event.repeat||event.ctrlKey||event.metaKey||event.altKey)return;
 const active=document.activeElement;
 if(active && ["INPUT","TEXTAREA","SELECT"].includes(active.tagName))return;
 inspectSurface();
});
