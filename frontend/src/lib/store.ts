import { create } from "zustand";

interface OrbisStore {
  selectedObjectId: string | null;
  orbitVisible: boolean;
  autoRotate: boolean;
  live: boolean;
  playbackRate: number;
  setSelectedObject: (id: string | null) => void;
  setOrbitVisible: (value: boolean) => void;
  setAutoRotate: (value: boolean) => void;
  setLive: (value: boolean) => void;
  setPlaybackRate: (value: number) => void;
}

export const useOrbisStore = create<OrbisStore>((set) => ({
  selectedObjectId: null, orbitVisible: true, autoRotate: true, live: true, playbackRate: 1,
  setSelectedObject: (selectedObjectId) => set({ selectedObjectId }),
  setOrbitVisible: (orbitVisible) => set({ orbitVisible }),
  setAutoRotate: (autoRotate) => set({ autoRotate }),
  setLive: (live) => set({ live }),
  setPlaybackRate: (playbackRate) => set({ playbackRate }),
}));