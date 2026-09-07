import { useMemo, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { useQuery } from "@tanstack/react-query";
import * as THREE from "three";
import { apiGet } from "@/lib/api";
import type { GeographyData, GeographyLabel } from "@/lib/orbis";

const point = (lon: number, lat: number, radius = 1.002) => { const a = lat * Math.PI / 180, b = lon * Math.PI / 180; return new THREE.Vector3(radius * Math.cos(a) * Math.cos(b), radius * Math.sin(a), radius * Math.cos(a) * Math.sin(b)); };
export default function GeographyLayer({ level }: { level: number }) {
  const country = useQuery({ queryKey: ["geography", "countries"], queryFn: () => apiGet<GeographyData>("/geography/countries"), staleTime: Infinity });
  const region = useQuery({ queryKey: ["geography", "regions"], queryFn: () => apiGet<GeographyData>("/geography/regions"), enabled: level >= 2, staleTime: Infinity });
  const city = useQuery({ queryKey: ["geography", "cities"], queryFn: () => apiGet<GeographyData>("/geography/cities"), enabled: level >= 3, staleTime: Infinity });
  const datasets = useMemo(() => [!country.isError ? country.data : undefined, level >= 2 && !region.isError ? region.data : undefined].filter((d): d is GeographyData => !!d), [country.data, country.isError, region.data, region.isError, level]);
  const lines = useMemo(() => {
    const array: number[] = [];
    for (const d of datasets) for (const line of d.lines) for (let i = 1; i < line.length; i++) { const a = point(line[i-1][0],line[i-1][1]); const b = point(line[i][0],line[i][1]); if(a.distanceTo(b) < .2) array.push(...a.toArray(),...b.toArray()); }
    return new Float32Array(array);
  }, [datasets]);
  const candidates = useMemo(() => {
    const labels = level >= 3 ? city.data?.labels : level >= 2 ? region.data?.labels : level >= 1 ? country.data?.labels : [];
    return (labels || []).map(label => ({ label, position: point(label.longitude, label.latitude, 1.007) }));
  }, [level, city.data, region.data, country.data]);
  const [visible, setVisible] = useState<{ label: GeographyLabel; position: THREE.Vector3 }[]>([]);
  const tick = useMemo(() => ({ last: 0 }), []);
  useFrame(({ camera, clock, size }) => {
    if(clock.elapsedTime - tick.last < .45) return; tick.last = clock.elapsedTime;
    const projected: { x: number; y: number }[] = [];
    const chosen = candidates.filter(item => {
      if (item.position.clone().normalize().dot(camera.position.clone().sub(item.position).normalize()) < .35) return false;
      const p = item.position.clone().project(camera);
      if(Math.abs(p.x) > .84 || Math.abs(p.y) > .85 || p.z > 1) return false;
      const x=p.x*size.width/2,y=p.y*size.height/2;
      if(projected.some(q=>Math.abs(q.x-x)<95 && Math.abs(q.y-y)<30))return false;
      projected.push({x,y}); return projected.length<=12;
    });
    setVisible(chosen);
  });
  return <group><lineSegments><bufferGeometry><bufferAttribute attach="attributes-position" args={[lines,3]} /></bufferGeometry><lineBasicMaterial color="#6598a5" transparent opacity={level === 0 ? .16 : .38} depthWrite={false} /></lineSegments>{visible.map(({label,position})=><Html key={`${label.name}-${label.longitude}`} position={position} center style={{pointerEvents:"none"}}><div data-testid={`geography-label-${label.name.toLowerCase().replace(/[^a-z0-9]/g,"-")}`} className="whitespace-nowrap font-mono text-[9px] tracking-wider text-slate-200 [text-shadow:0_1px_4px_#000]">{label.capital ? "◇ " : ""}{label.name}</div></Html>)}</group>;
}