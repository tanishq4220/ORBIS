import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./api";
import type { Analytics, ConnectionConfig, HealthResponse, OrbisObject, PositionsResponse, ScreeningHistoryItem, Summary, TelemetryResponse, TrajectoryResponse } from "./orbis";
import { useOrbisStore } from "./store";

export function useDebounced<T>(value: T, delay = 280): T {
  const [result, setResult] = useState(value);
  useEffect(() => { const timer = setTimeout(() => setResult(value), delay); return () => clearTimeout(timer); }, [value, delay]);
  return result;
}

export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: () => apiGet<HealthResponse>("/health"), refetchInterval: 30000, staleTime: 15000, retry: false });
export const useConnection = () => useQuery({ queryKey: ["connection"], queryFn: () => apiGet<ConnectionConfig>("/connection"), staleTime: Infinity });

export function useSummary() {
  return useQuery({ queryKey: ["summary"], queryFn: async () => {
    const s = await apiGet<Summary>("/summary");
    const counts = [s.total_objects, s.satellites, s.debris, s.fast, s.deep, s.insufficient_data, s.reliable, s.low_confidence];
    if (counts.some(n => !Number.isInteger(n) || n < 0) || s.satellites + s.debris !== s.total_objects || s.fast + s.deep + s.insufficient_data !== s.total_objects || s.reliable + s.low_confidence > s.total_objects)
      throw new Error("DATA INTEGRITY ALERT — backend catalog counts do not reconcile");
    return s;
  }, staleTime: 30000, refetchInterval: 60000, retry: false });
}

export const useAnalytics = () => useQuery({ queryKey: ["analytics"], queryFn: () => apiGet<Analytics>("/analytics"), staleTime: 30000, retry: false });
export const useHistory = () => useQuery({ queryKey: ["screen-history"], queryFn: () => apiGet<{ total: number; items: ScreeningHistoryItem[] }>("/conjunctions/history"), staleTime: 10000, retry: false });

export function usePositions() {
  const live = useOrbisStore(s => s.live);
  return useQuery({ queryKey: ["positions"], queryFn: () => apiGet<PositionsResponse>("/positions"), staleTime: 10000, refetchInterval: live ? 15000 : false, retry: false });
}

export function useObjectData(id: string | null) {
  const live = useOrbisStore(s => s.live);
  const index = useOrbisStore(s => s.telemetryIndex);
  const object = useQuery({ queryKey: ["object", id], queryFn: () => apiGet<OrbisObject>(`/objects/${id}`), enabled: !!id, staleTime: 60000, retry: false });
  const state = useQuery({ queryKey: ["object-state", id], queryFn: () => apiGet<OrbisObject>(`/objects/${id}/state`), enabled: !!id && live, refetchInterval: live ? 15000 : false, staleTime: 10000, retry: false });
  const telemetry = useQuery({ queryKey: ["telemetry", id], queryFn: () => apiGet<TelemetryResponse>(`/objects/${id}/telemetry?hours=1&step_minutes=1`), enabled: !!id, staleTime: 60000, retry: false });
  const start = !telemetry.isError ? telemetry.data?.points[0]?.utc : undefined;
  const trajectory = useQuery({ queryKey: ["trajectory", id, start], queryFn: () => apiGet<TrajectoryResponse>(`/objects/${id}/trajectory?hours=1.5&step_minutes=1&start_utc=${encodeURIComponent(start || "")}`), enabled: !!id && !!start, staleTime: 60000, retry: false });
  const current = live ? (!state.isError ? state.data?.state : undefined) : (!telemetry.isError ? telemetry.data?.points[index] : undefined);
  return { object, state, trajectory, telemetry, current };
}

export type ObjectData = ReturnType<typeof useObjectData>;
export const number = (v: number | null | undefined, digits = 2, unit = "") => v == null || !Number.isFinite(v) ? "N/A" : `${v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit}`;
export const percent = (v: number | null | undefined) => v == null ? "N/A" : number(v * 100, 1, "%");
export const utc = (v: string | null | undefined) => v ? v.replace("T", " ").replace(/\.\d+Z$/, "Z") : "DATA UNAVAILABLE";