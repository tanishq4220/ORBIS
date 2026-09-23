import { create } from "zustand";

interface OrbisStore {
  selectedObjectId: string | null;
  orbitVisible: boolean;
  autoRotate: boolean;
  live: boolean;
  playbackRate: number;
  playing: boolean;
  telemetryIndex: number;
  focusRevision: number;
  satellitesVisible: boolean;
  debrisVisible: boolean;
  geographyVisible: boolean;
  setPlaying: (value: boolean) => void;
  setTelemetryIndex: (value: number) => void;
  focusObject: () => void;
  setLayer: (layer: "satellitesVisible" | "debrisVisible" | "geographyVisible", value: boolean) => void;
  setSelectedObject: (id: string | null) => void;
  setOrbitVisible: (value: boolean) => void;
  setAutoRotate: (value: boolean) => void;
  setLive: (value: boolean) => void;
  setPlaybackRate: (value: number) => void;
}

export const useOrbisStore = create<OrbisStore>((set) => ({
  selectedObjectId: null, orbitVisible: true, autoRotate: false, live: true, playbackRate: 10,
  playing: false, telemetryIndex: 0, focusRevision: 0, satellitesVisible: true, debrisVisible: true, geographyVisible: true,
  setSelectedObject: (selectedObjectId) => set((state) => selectedObjectId === state.selectedObjectId ? { focusRevision: state.focusRevision + 1 } : { selectedObjectId, live: true, playing: false, telemetryIndex: 0, focusRevision: state.focusRevision + 1 }),
  setPlaying: (playing) => set({ playing, live: false }),
  setTelemetryIndex: (telemetryIndex) => set({ telemetryIndex, live: false }),
  focusObject: () => set((state) => ({ focusRevision: state.focusRevision + 1 })),
  setLayer: (layer, value) => set({ [layer]: value }),
  setOrbitVisible: (orbitVisible) => set({ orbitVisible }),
  setAutoRotate: (autoRotate) => set({ autoRotate }),
  setLive: (live) => set({ live, playing: false, telemetryIndex: 0 }),
  setPlaybackRate: (playbackRate) => set({ playbackRate }),
}));