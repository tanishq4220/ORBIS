/**
 * Adapted from mitchcamza/Earth3D, revision 1d151516f8041e5bec91aee83f7d8261e9f6604d.
 * Shader techniques credited upstream to Bruno Simon, https://threejs-journey.com.
 * See /assets/earth3d/ATTRIBUTION.txt for source, license and texture credits.
 * These shaders shade a surface only; they do not propagate any orbital data.
 */
export const earthVertexShader = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vec4 modelPosition = modelMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * viewMatrix * modelPosition;
    vNormal = (modelMatrix * vec4(normal, 0.0)).xyz;
    vPosition = modelPosition.xyz;

    // ORBIS: +X = Greenwich, +Y = north, +Z = 90 degrees east.
    // SphereGeometry runs longitude in the opposite direction. Mirror the UV,
    // not the globe_xyz data. This keeps all four texture layers registered
    // with the existing Natural Earth overlays and backend ECEF positions.
    vUv = vec2(1.0 - uv.x, uv.y);
  }
`;

export const earthFragmentShader = /* glsl */ `
  uniform sampler2D uDayTexture;
  uniform sampler2D uNightTexture;
  uniform sampler2D uSpecularCloudsTexture;
  uniform vec3 uSunDirection;
  uniform vec3 uAtmosphereDayColor;
  uniform vec3 uAtmosphereTwilightColor;

  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vec3 viewDirection = normalize(vPosition - cameraPosition);
    vec3 normal = normalize(vNormal);
    float sunOrientation = dot(uSunDirection, normal);

    // Earth3D's smooth terminator and archival city-light composite.
    float dayMix = smoothstep(-0.25, 0.5, sunOrientation);
    vec3 dayColor = texture2D(uDayTexture, vUv).rgb;
    vec3 nightColor = texture2D(uNightTexture, vUv).rgb;
    vec3 color = mix(nightColor, dayColor, dayMix);

    // Packed upstream texture: R = water/specular mask, G = cloud coverage.
    // Implement the water glint in GLSL: assigning metalnessMap/bumpMap to
    // ShaderMaterial (as in the standalone demo) does not activate shading.
    vec2 specularClouds = texture2D(uSpecularCloudsTexture, vUv).rg;
    vec3 reflection = reflect(-uSunDirection, normal);
    float specular = pow(max(dot(reflection, -viewDirection), 0.0), 32.0);
    color += vec3(1.0, 0.94, 0.84) * specular * specularClouds.r * dayMix * 0.55;

    // Static imagery, NOT live weather. No free-running texture rotation:
    // the geographic surface stays locked to the real ECEF catalog.
    float cloudsMix = smoothstep(0.5, 1.0, specularClouds.g) * dayMix;
    color = mix(color, vec3(1.0), cloudsMix);

    float fresnel = pow(clamp(dot(viewDirection, normal) + 1.0, 0.0, 1.0), 2.0);
    float atmosphereDayMix = smoothstep(-0.5, 1.0, sunOrientation);
    vec3 atmosphereColor = mix(uAtmosphereTwilightColor, uAtmosphereDayColor, atmosphereDayMix);
    color = mix(color, atmosphereColor, fresnel * atmosphereDayMix);

    gl_FragColor = vec4(color, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export const atmosphereVertexShader = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vec4 modelPosition = modelMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * viewMatrix * modelPosition;
    vNormal = (modelMatrix * vec4(normal, 0.0)).xyz;
    vPosition = modelPosition.xyz;
  }
`;

export const atmosphereFragmentShader = /* glsl */ `
  uniform vec3 uSunDirection;
  uniform vec3 uAtmosphereDayColor;
  uniform vec3 uAtmosphereTwilightColor;
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vec3 viewDirection = normalize(vPosition - cameraPosition);
    vec3 normal = normalize(vNormal);
    float sunOrientation = dot(uSunDirection, normal);
    float atmosphereDayMix = smoothstep(-0.5, 1.0, sunOrientation);
    vec3 atmosphereColor = mix(uAtmosphereTwilightColor, uAtmosphereDayColor, atmosphereDayMix);
    vec3 color = atmosphereColor * (1.0 + atmosphereDayMix);
    float edgeAlpha = smoothstep(0.0, 0.5, dot(viewDirection, normal));
    float dayAlpha = smoothstep(-0.5, 0.0, sunOrientation);
    gl_FragColor = vec4(color, edgeAlpha * dayAlpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;