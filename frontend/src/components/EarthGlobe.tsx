import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Billboard, Line, OrbitControls, Stars, useTexture } from "@react-three/drei";
import { Component, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { OrbitControls as Controls } from "three-stdlib";
import { useQuery } from "@tanstack/react-query";
import { Crosshair, Globe2, Layers3, Minus, Pause, Play, Plus, RotateCcw } from "lucide-react";
import * as THREE from "three";
import { Button } from "@/components/ui/button";
import { apiGet } from "@/lib/api";
import { useOrbisStore } from "@/lib/store";
import type { EnvironmentState, ObjectState, PositionsResponse, TrajectoryResponse } from "@/lib/orbis";
import GeographyLayer from "./GeographyLayer";

const vertex = `varying vec3 vP; varying vec3 vW; varying vec2 vTex; void main(){vP=position;vTex=vec2(1.-uv.x,uv.y);vW=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
const uvCode = `vec3 n=normalize(vP);vec2 coord=vTex;float lit=dot(n,normalize(sun));`;
function Earth({ sun }: { sun: number[] }) {
  const [day,night,cloud] = useTexture(["/assets/earth-day.jpg","/assets/earth-night.jpg","/assets/earth-clouds.jpg"]);
  const uniforms = useMemo(()=>({day:{value:day},night:{value:night},cloud:{value:cloud},sun:{value:new THREE.Vector3(sun[0],sun[1],sun[2])}}),[day,night,cloud,sun]);
  return <group><mesh onPointerMove={e=>e.stopPropagation()} onClick={e=>e.stopPropagation()}><sphereGeometry args={[1,96,64]} /><shaderMaterial uniforms={uniforms} vertexShader={vertex} fragmentShader={`uniform sampler2D day;uniform sampler2D night;uniform vec3 sun;varying vec3 vP;varying vec2 vTex;void main(){${uvCode} vec3 d=texture2D(day,coord).rgb;vec3 lights=texture2D(night,coord).rgb;float daylight=smoothstep(-.13,.2,lit);vec3 color=d*(.045+max(lit,0.)*.94)+lights*(1.-daylight)*.62;gl_FragColor=vec4(color,1.);}`} /></mesh>
    <mesh><sphereGeometry args={[1.005,64,48]} /><shaderMaterial uniforms={uniforms} transparent depthWrite={false} vertexShader={vertex} fragmentShader={`uniform sampler2D cloud;uniform vec3 sun;varying vec3 vP;varying vec2 vTex;void main(){${uvCode} float c=texture2D(cloud,coord).r;gl_FragColor=vec4(vec3(.91,.95,1.)*(.09+max(lit,0.)),c*.4);}`} /></mesh>
    <mesh><sphereGeometry args={[1.022,96,64]} /><shaderMaterial transparent depthWrite={false} side={THREE.BackSide} uniforms={{sun:{value:new THREE.Vector3(sun[0],sun[1],sun[2])}}} vertexShader={vertex} fragmentShader={`varying vec3 vP;varying vec3 vW;uniform vec3 sun;void main(){float rim=pow(1.-max(dot(normalize(vP),normalize(cameraPosition-vW)),0.),4.);float lit=max(dot(normalize(vP),normalize(sun)),.08);gl_FragColor=vec4(.19,.49,.73,rim*lit*.17);}`} /></mesh>
  </group>;
}

function CatalogPoints({ positions, onSelect, onHover, highlights }: { positions?: PositionsResponse; onSelect:(id:string)=>void; onHover:(s:string)=>void; highlights:string[] }) {
  const satellites=useOrbisStore(s=>s.satellitesVisible),debris=useOrbisStore(s=>s.debrisVisible),selected=useOrbisStore(s=>s.selectedObjectId);
  const data=useMemo(()=>{
    const coordinates:number[]=[],colors:number[]=[],ids:string[]=[]; const hot=new Set(highlights);
    if(positions)for(let i=0;i<positions.ids.length;i++){
      if(positions.valid[i]!==1 || positions.ids[i]===selected || (positions.type_codes[i]===1 ? !debris : !satellites))continue;
      coordinates.push(...positions.positions.slice(i*3,i*3+3));ids.push(positions.ids[i]);
      const c=new THREE.Color(hot.has(positions.ids[i])?"#ff5b55":positions.type_codes[i]===1?"#dd9e54":"#9bdce8");colors.push(c.r,c.g,c.b);
    }
    return {coordinates:new Float32Array(coordinates),colors:new Float32Array(colors),ids};
  },[positions,satellites,debris,selected,highlights]);
  if(!data.ids.length)return null;
  return <points onClick={e=>{if(e.index!=null){e.stopPropagation();onSelect(data.ids[e.index]);}}} onPointerMove={e=>{if(e.index!=null){e.stopPropagation();onHover(`CATALOG ${data.ids[e.index]} · CLICK TO INSPECT`);}}} onPointerOut={()=>onHover("")}><bufferGeometry><bufferAttribute attach="attributes-position" args={[data.coordinates,3]} /><bufferAttribute attach="attributes-color" args={[data.colors,3]} /></bufferGeometry><shaderMaterial transparent depthWrite={false} vertexColors vertexShader={`varying vec3 c;varying float fade;void main(){c=color;vec4 p=modelViewMatrix*vec4(position,1.);float distanceToCamera=length(p.xyz);fade=clamp(1.8/distanceToCamera,.18,.78);gl_PointSize=clamp(4.0/max(-p.z,.1),1.,3.6);gl_Position=projectionMatrix*p;}`} fragmentShader={`varying vec3 c;varying float fade;void main(){float r=length(gl_PointCoord-.5);if(r>.5)discard;float a=(1.-smoothstep(.15,.5,r))*fade;gl_FragColor=vec4(c,a);}`} /></points>;
}

function SelectedMarker({state}:{state?:ObjectState}){
  const ref=useRef<THREE.Mesh>(null);
  useFrame(({clock})=>{if(ref.current)ref.current.scale.setScalar(1+Math.sin(clock.elapsedTime*2)*.12);});
  const p=state?.globe_xyz;if(!p)return null;
  return <Billboard position={[p.x,p.y,p.z]}><mesh ref={ref}><ringGeometry args={[.016,.019,40]} /><meshBasicMaterial color="#bbf7ff" transparent opacity={.9} depthWrite={false} /></mesh><mesh><circleGeometry args={[.007,20]} /><meshBasicMaterial color="#c8fcff" /></mesh></Billboard>;
}

function CameraRig({command,state,onLevel,sun}:{command:{kind:string;seq:number};state?:ObjectState;onLevel:(n:number)=>void;sun?:number[]}){
  const {camera,invalidate}=useThree();const controls=useRef<Controls>(null);const destination=useRef<THREE.Vector3|null>(null);const target=useRef(new THREE.Vector3());
  const auto=useOrbisStore(s=>s.autoRotate),focus=useOrbisStore(s=>s.focusRevision),id=useOrbisStore(s=>s.selectedObjectId);
  const lastFocus=useRef("");const level=useRef(-1);
  const initialized=useRef(false);
  useEffect(()=>{if(sun&&!initialized.current&&!id){initialized.current=true;const view=new THREE.Vector3(sun[0],sun[1],sun[2]).applyAxisAngle(new THREE.Vector3(0,1,0),.7);view.y+=.3;camera.position.copy(view.normalize().multiplyScalar(3.3));}},[sun,id,camera]);
  useEffect(()=>{
    if(!controls.current)return;
    const direction=camera.position.clone().sub(controls.current.target).normalize();
    if(command.kind==="reset"){target.current.set(0,0,0);destination.current=new THREE.Vector3(2.1,1.15,2.2);useOrbisStore.getState().setAutoRotate(false);}
    if(command.kind==="in" || command.kind==="out"){target.current.copy(controls.current.target);destination.current=camera.position.clone().sub(target.current).multiplyScalar(command.kind==="in"?.78:1.25).add(target.current);}
    if(["global","regional","local"].includes(command.kind)){target.current.set(0,0,0);destination.current=direction.multiplyScalar(command.kind==="global"?3.3:command.kind==="regional"?1.75:1.18);}
  },[command,camera]);
  useFrame((_,delta)=>{
    const c=controls.current;if(!c)return;
    const key=`${id}-${focus}`;
    if(state?.globe_xyz && key!==lastFocus.current){lastFocus.current=key;const p=new THREE.Vector3(state.globe_xyz.x,state.globe_xyz.y,state.globe_xyz.z);destination.current=p.clone().normalize().multiplyScalar(Math.max(2.15,p.length()+.65));target.current.copy(p).multiplyScalar(.3);}
    if(destination.current){camera.position.lerp(destination.current,1-Math.exp(-delta*3));c.target.lerp(target.current,1-Math.exp(-delta*3));if(camera.position.distanceTo(destination.current)<.005)destination.current=null;else invalidate();}
    const distance=camera.position.length();const next=distance<1.32?3:distance<1.65?2:distance<2.3?1:0;
    if(next!==level.current){level.current=next;onLevel(next);}
    c.update();
  });
  return <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={.065} autoRotate={auto} autoRotateSpeed={.22} enablePan minDistance={1.06} maxDistance={15} rotateSpeed={.35} zoomSpeed={.6} onStart={()=>{destination.current=null;useOrbisStore.getState().setAutoRotate(false);}} />;
}

class GlobeBoundary extends Component<{children:ReactNode},{failed:boolean}>{
  state={failed:false};static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?<div data-testid="globe-render-error" className="grid h-full place-items-center p-8 text-center font-mono text-xs text-amber-200">3D VIEW UNAVAILABLE · Your browser needs WebGL. Orbital data remains available in the catalog.</div>:this.props.children;}
}

export default function EarthGlobe({positions,onSelect,current,trajectory,highlights=[]}:{positions?:PositionsResponse;onSelect:(id:string)=>void;current?:ObjectState;trajectory?:TrajectoryResponse;highlights?:string[]}){
  const [command,setCommand]=useState({kind:"none",seq:0});const [level,setLevel]=useState(0);const [hover,setHover]=useState("");const [layers,setLayers]=useState(false);
  const [contextLost,setContextLost]=useState(false);const [canvasKey,setCanvasKey]=useState(0);
  const {autoRotate,setAutoRotate,orbitVisible,geographyVisible,satellitesVisible,debrisVisible,setLayer,live}=useOrbisStore();
  const epoch=current?.utc||positions?.utc;
  const env=useQuery({queryKey:["environment",epoch],queryFn:()=>apiGet<EnvironmentState>(`/environment${epoch?`?utc=${encodeURIComponent(epoch)}`:""}`),staleTime:30000});
  const orbit=useMemo(()=>trajectory?.samples.filter(s=>s.globe_xyz).map(s=>[s.globe_xyz!.x,s.globe_xyz!.y,s.globe_xyz!.z] as [number,number,number])||[],[trajectory]);
  const act=(kind:string)=>setCommand(c=>({kind,seq:c.seq+1}));
  return <div data-testid="earth-globe-container" className="globe-stage"><GlobeBoundary><Canvas key={canvasKey} frameloop="demand" camera={{position:[2.1,1.15,2.2],fov:42,near:.01,far:200}} dpr={1} raycaster={{params:{Points:{threshold:.008},Line:{threshold:.005},Mesh:{},LOD:{},Sprite:{}}}} gl={{antialias:false,powerPreference:"high-performance"}} onCreated={({gl})=>{gl.domElement.addEventListener("webglcontextlost",e=>{e.preventDefault();setContextLost(true);});gl.domElement.addEventListener("webglcontextrestored",()=>setContextLost(false));}}><color attach="background" args={["#04090f"]} /><Stars radius={75} depth={20} count={700} factor={.55} saturation={0} fade speed={0} /><Suspense fallback={null}>{env.data?<Earth sun={env.data.sun_direction}/>:null}{geographyVisible?<GeographyLayer level={level}/>:null}</Suspense>{live?<CatalogPoints positions={positions} onSelect={onSelect} onHover={setHover} highlights={highlights}/>:null}{orbitVisible&&orbit.length>1&&level>0?<Line points={orbit} color="#62aebc" lineWidth={.85} transparent opacity={.5} depthWrite={false}/>:null}<SelectedMarker state={current}/><CameraRig command={command} state={current} onLevel={setLevel} sun={env.data?.sun_direction}/></Canvas></GlobeBoundary>
    {contextLost?<div data-testid="globe-context-lost" className="absolute inset-0 z-20 grid place-items-center bg-[#08121d]/95 p-8 text-center"><div><p className="font-mono text-xs text-amber-200">3D RENDERER INTERRUPTED</p><p className="mt-2 text-xs text-slate-400">Your graphics context was interrupted. Scientific data is unchanged.</p><Button data-testid="restore-globe-button" variant="outline" className="mt-4" onClick={()=>{setContextLost(false);setCanvasKey(k=>k+1);}}>RESTORE 3D VIEW</Button></div></div>:null}
    <div className="pointer-events-none absolute inset-x-4 top-4 flex justify-between"><div data-testid="globe-reference-frame" className="font-mono text-[9px] leading-5 tracking-wider text-slate-400"><span className="text-cyan-200">EARTH / ECEF</span><br/>{["GLOBAL VIEW","REGIONAL VIEW","LOCAL VIEW","CITY VIEW"][level]}<br/><span className="text-slate-500">{live?"SGP4 CATALOG SNAPSHOT":"SELECTED-OBJECT REPLAY · CATALOG HIDDEN"}</span></div><div data-testid="globe-north-indicator" className="font-mono text-[10px] text-slate-500">Y ↑ N</div></div>
    <div className="absolute right-3 top-20 flex flex-col gap-1 rounded border border-slate-700/40 bg-[#0b131d]/90 p-1"><Button data-testid="globe-zoom-in" title="Zoom in" variant="ghost" size="icon-sm" onClick={()=>act("in")}><Plus size={15}/></Button><Button data-testid="globe-zoom-out" title="Zoom out" variant="ghost" size="icon-sm" onClick={()=>act("out")}><Minus size={15}/></Button><Button data-testid="globe-reset" title="Reset view" variant="ghost" size="icon-sm" onClick={()=>act("reset")}><RotateCcw size={14}/></Button><Button data-testid="globe-auto-rotate" title={autoRotate?"Pause camera rotation":"Auto rotate camera"} variant="ghost" size="icon-sm" onClick={()=>setAutoRotate(!autoRotate)}>{autoRotate?<Pause size={14}/>:<Play size={14}/>}</Button><Button data-testid="globe-layers" title="Map layers" variant="ghost" size="icon-sm" onClick={()=>setLayers(!layers)}><Layers3 size={14}/></Button></div>
    {layers?<div data-testid="globe-layer-menu" className="absolute right-14 top-20 w-44 space-y-3 rounded border border-slate-700 bg-[#0c1622] p-4">{[["satellitesVisible","Satellites",satellitesVisible],["debrisVisible","Debris",debrisVisible],["geographyVisible","Geography",geographyVisible]].map(([key,label,checked])=><label key={String(key)} className="flex items-center gap-2 text-xs text-slate-300"><input data-testid={`layer-${key}`} type="checkbox" checked={!!checked} onChange={e=>setLayer(key as "satellitesVisible"|"debrisVisible"|"geographyVisible",e.target.checked)} className="accent-cyan-300"/>{label}</label>)}</div>:null}
    {hover?<div data-testid="globe-hover-tooltip" className="pointer-events-none absolute bottom-20 left-1/2 -translate-x-1/2 rounded border border-cyan-400/25 bg-[#0a1520] px-3 py-2 font-mono text-[9px] text-cyan-100">{hover}</div>:null}
    <div className="absolute bottom-11 left-3 flex gap-1">{[["global",Globe2],["regional",Crosshair],["local",Plus]].map(([name,Icon])=>{const I=Icon as typeof Globe2;return <Button key={String(name)} data-testid={`camera-${name}`} variant="ghost" size="xs" className="bg-[#09121c]/80 font-mono text-[8px] text-slate-400" onClick={()=>act(String(name))}><I size={10}/>{String(name).toUpperCase()}</Button>;})}</div>
    <div data-testid="globe-legend" className="absolute inset-x-0 bottom-0 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-800/60 bg-[#09111a]/95 px-4 py-2 font-mono text-[8px] text-slate-400">{[["#9bdce8","SATELLITE"],["#dd9e54","DEBRIS"],["#c8fcff","SELECTED"],["#62aebc","ORBIT"],["#ff5b55","POTENTIAL CONJUNCTION"]].map(([c,label])=><span key={label} data-testid={`legend-${label.toLowerCase().replaceAll(" ","-")}`} className="flex items-center gap-1.5"><i className="h-1 w-1 rounded-full" style={{background:c}}/>{label}</span>)}<span className="ml-auto hidden text-slate-500 2xl:inline">NASA SURFACE · STATIC CLOUDS · NATURAL EARTH</span></div>
  </div>;
}