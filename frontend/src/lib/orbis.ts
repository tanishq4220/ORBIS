export type Decision = "FAST" | "DEEP" | "INSUFFICIENT_DATA" | string;
export type MlPrediction = "RELIABLE" | "LOW_CONFIDENCE" | string;

export interface AuthUser { id: string; email: string; name: string }
export interface Vec3 { x: number; y: number; z: number }
export interface Vel3 { vx: number; vy: number; vz: number }
export interface ObjectState {
  utc: string; sgp4_status: string; sgp4_error_code: number;
  position_teme_km: Vec3 | null; velocity_teme_km_s: Vel3 | null;
  position_ecef_km: Vec3 | null; latitude_deg: number | null; longitude_deg: number | null;
  altitude_km: number | null; speed_km_s: number | null; globe_xyz: Vec3 | null;
}
export interface OrbisObject {
  id: string; name: string | null; type: string | null; epoch: string | null;
  data_age_days: number | null; data_age_confidence: number | null;
  trajectory_consistency: number | null; track_confidence: number | null;
  prediction_error_km: number | null; prediction_confidence: number | null;
  prediction_horizon_hours: number | null; model_confidence: number | null;
  ml_prediction: MlPrediction | null; aci: number | null; decision: Decision | null;
  tle_line1?: string | null; tle_line2?: string | null; state?: ObjectState;
}
export interface Summary {
  total_objects: number; satellites: number; debris: number; fast: number; deep: number;
  insufficient_data: number; reliable: number; low_confidence: number;
  aci: { mean: number | null; minimum: number | null; maximum: number | null };
  model_confidence: { mean: number | null; minimum: number | null; maximum: number | null };
  data_age_days: { mean: number | null; minimum: number | null; maximum: number | null };
  subsystems: Record<string, string>;
}
export interface HealthResponse { status: string; service: string; utc: string; aci_output_available: boolean; object_count: number; sgp4_cache_size: number; startup_error: string | null; subsystems: Record<string, string> }
export interface PositionsResponse { utc: string; count: number; ids: string[]; positions: number[]; valid: number[]; type_codes: number[] }
export interface PaginatedObjects { page: number; limit: number; total: number; total_pages: number; objects: OrbisObject[] }
export interface TrajectoryResponse { object_id: string; name?: string; status: string; sample_count?: number; samples: ObjectState[] }
export interface TelemetryPoint { utc: string; altitude_km: number | null; speed_km_s: number | null; latitude_deg: number | null; longitude_deg: number | null; position_teme_km: Vec3 | null; velocity_teme_km_s: Vel3 | null; globe_xyz: Vec3 | null }
export interface TelemetryResponse { object_id: string; status: string; points: TelemetryPoint[] }
export interface ScreeningRow { object_id: string; object_name: string | null; object_type: string | null; minimum_separation_km: number; tca_utc: string; status: string }
export interface ScreeningResult { screening_id: string; status: string; prototype?: boolean; disclaimer?: string; target_id: string; target_name?: string | null; timestamp_utc: string; completed_utc?: string; start_utc?: string; time_step_min: number; window_min: number; threshold_km: number; top_n?: number; objects_screened?: number; potential_count?: number; minimum_separation_km: number | null; tca_utc: string | null; results: ScreeningRow[]; full_results?: ScreeningRow[]; error?: string }
export interface Analytics { type_distribution: { label: string; count: number }[]; decision_distribution: { label: string; count: number }[]; ml_distribution: { label: string; count: number }[]; aci_histogram: Histogram[]; model_confidence_histogram: Histogram[]; data_age_histogram: Histogram[]; trajectory_consistency_histogram: Histogram[]; summary: Summary }
export interface Histogram { bin_start: number; bin_end: number; count: number }