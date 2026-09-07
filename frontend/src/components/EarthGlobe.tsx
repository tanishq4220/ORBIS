import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars, useTexture } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { PositionsResponse } from "@/lib/orbis";

function Earth() {
  const texture = useTexture("https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg");
  const clouds = useTexture("https://threejs.org/examples/textures/planets/earth_clouds_1024.png");
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => { if (ref.current) ref.current.rotation.y += delta * 0.025; });
  return <group rotation={[0.1, -0.5, 0]}><mesh ref={ref}><sphereGeometry args={[1, 64, 64]} /><meshStandardMaterial map={texture} roughness={0.82} metalness={0.05} /></mesh><mesh rotation={[0.1, -0.5, 0]}><sphereGeometry args={[1.008, 48, 48]} /><meshPhongMaterial map={clouds} transparent opacity={0.17} depthWrite={false} /></mesh><mesh><sphereGeometry args={[1.07, 48, 48]} /><meshBasicMaterial color="#22d3ee" transparent opacity={0.075} side={THREE.BackSide} /></mesh></group>;
}

function CatalogPoints({ positions, onSelect }: { positions?: PositionsResponse; onSelect: (id: string) => void }) {
  const points = useMemo(() => { if (!positions) return null; const valid = positions.positions.length / 3; const data = new Float32Array(positions.positions); const colors = new Float32Array(valid * 3); for (let i = 0; i < valid; i += 1) { const debris = positions.type_codes[i] === 1; const color = debris ? new THREE.Color("#f59e0b") : new THREE.Color("#22d3ee"); colors.set([color.r, color.g, color.b], i * 3); } return { data, colors }; }, [positions]);
  if (!points || !positions) return null;
  return <points onPointerDown={(event) => { const index = (event as unknown as { index?: number }).index; if (index !== undefined && positions.valid[index] === 1) onSelect(positions.ids[index]); }}><bufferGeometry><bufferAttribute attach="attributes-position" args={[points.data, 3]} /><bufferAttribute attach="attributes-color" args={[points.colors, 3]} /></bufferGeometry><pointsMaterial size={0.014} vertexColors transparent opacity={0.9} sizeAttenuation /></points>;
}

export default function EarthGlobe({ positions, onSelect }: { positions?: PositionsResponse; onSelect: (id: string) => void }) {
  return <div data-testid="earth-globe-container" className="absolute inset-0"><Canvas camera={{ position: [0, 0.2, 2.65], fov: 42 }} dpr={[1, 1.5]}><color attach="background" args={["#050811"]} /><ambientLight intensity={0.38} /><directionalLight position={[4, 3, 4]} intensity={2.2} color="#dbeafe" /><directionalLight position={[-4, -2, -4]} intensity={0.28} color="#155e75" /><Stars radius={80} depth={45} count={1900} factor={2.2} saturation={0.2} fade speed={0.12} /><Earth /><CatalogPoints positions={positions} onSelect={onSelect} /><OrbitControls enablePan={false} minDistance={1.6} maxDistance={5.5} rotateSpeed={0.42} zoomSpeed={0.7} /></Canvas></div>;
}