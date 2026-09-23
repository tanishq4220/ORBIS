import { useLayoutEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { useTexture } from "@react-three/drei";
import * as THREE from "three";
import {
  atmosphereFragmentShader,
  atmosphereVertexShader,
  earthFragmentShader,
  earthVertexShader,
} from "./earth3dShaders";

/** Visual-only Earth3D port. ORBIS owns coordinates, epoch, selection and camera. */
export default function Earth3DSurface({ sun }: { sun: number[] }) {
  const { gl, invalidate } = useThree();
  const [day, night, specularClouds] = useTexture([
    "/assets/earth3d/2k_earth_daymap.jpg",
    "/assets/earth3d/night.jpg",
    "/assets/earth3d/specularClouds.jpg",
  ]);

  const uniforms = useMemo(() => ({
    uDayTexture: { value: day },
    uNightTexture: { value: night },
    uSpecularCloudsTexture: { value: specularClouds },
    uSunDirection: { value: new THREE.Vector3() },
    uAtmosphereDayColor: { value: new THREE.Color("#9fd8ff") },
    uAtmosphereTwilightColor: { value: new THREE.Color("#050c1f") },
  }), [day, night, specularClouds]);

  useLayoutEffect(() => {
    const anisotropy = Math.min(gl.capabilities.getMaxAnisotropy(), 8);
    for (const texture of [day, night, specularClouds]) {
      // Color maps are sRGB; the packed cloud/specular mask is linear data.
      texture.colorSpace = texture === specularClouds ? THREE.NoColorSpace : THREE.SRGBColorSpace;
      texture.anisotropy = anisotropy;
      texture.needsUpdate = true;
    }
    invalidate();
    // useTexture owns these cached textures; do not dispose shared maps on unmount.
  }, [day, night, specularClouds, gl, invalidate]);

  useLayoutEffect(() => {
    // Existing backend /environment follows the same live/replay epoch as ORBIS.
    uniforms.uSunDirection.value.set(sun[0], sun[1], sun[2]).normalize();
    invalidate();
  }, [sun, uniforms, invalidate]);

  return <group name="earth3d-visual-engine">
    <mesh name="earth3d-surface" onPointerMove={event => event.stopPropagation()} onClick={event => event.stopPropagation()}>
      <sphereGeometry args={[1, 96, 64]} />
      <shaderMaterial uniforms={uniforms} vertexShader={earthVertexShader} fragmentShader={earthFragmentShader} />
    </mesh>
    <mesh name="earth3d-atmosphere" scale={1.025} raycast={() => {}}>
      <sphereGeometry args={[1, 96, 64]} />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={atmosphereVertexShader}
        fragmentShader={atmosphereFragmentShader}
        side={THREE.BackSide}
        transparent
        depthWrite={false}
      />
    </mesh>
  </group>;
}