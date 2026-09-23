import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Crosshair, Zap } from "lucide-react";
import { apiGet } from "@/lib/api";
import { useHistory, useObjectData, number, percent } from "@/lib/data";
import { useOrbisStore } from "@/lib/store";
import type { PaginatedObjects } from "@/lib/orbis";
import {
  DataState,
  PageHeader,
  Panel,
  StatusChip,
} from "@/components/ConsolePrimitives";
import ObjectIntelligence, {
  ReliabilityContext,
} from "@/components/ObjectIntelligence";

export default function RiskWorkspace() {
  const navigate = useNavigate();
  const { selectedObjectId, setSelectedObject } = useOrbisStore();
  const data = useObjectData(selectedObjectId);
  const history = useHistory();
  const [filterType, setFilterType] = useState<string>("ALL");

  const objects = useQuery({
    queryKey: ["risk-objects", filterType],
    queryFn: () => {
      const typeParam = filterType !== "ALL" ? `&type=${filterType}` : "";
      return apiGet<PaginatedObjects>(
        `/objects?limit=25&sort=aci&order=asc${typeParam}`
      );
    },
    retry: false,
  });

  return (
    <div data-testid="risk-analysis-page" className="fade-enter space-y-6">
      <PageHeader
        eyebrow="EVIDENCE REVIEW / OPERATIONAL CONTEXT"
        title="Orbital Risk Analysis"
        description="Differentiate geometric spatial proximity from observational element reliability. An unscreened object is never presumed clear."
        action={
          <button
            onClick={() => navigate("/conjunctions")}
            className="flex items-center gap-1.5 rounded border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 font-mono text-[10px] font-bold text-amber-200 transition-colors hover:bg-amber-400/20"
          >
            SCREENING CONSOLE <ArrowUpRight size={12} />
          </button>
        }
      />

      {/* Distinction Header Callout */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded border border-amber-500/20 bg-amber-950/10 p-4">
          <div className="flex items-center gap-2 font-mono text-xs font-bold text-amber-300">
            <Crosshair size={14} /> 1. GEOMETRIC SEPARATION (KM)
          </div>
          <p className="mt-2 text-xs text-slate-300 leading-5">
            Physical miss distance between propagated orbits. Evaluated via 3D Euclidean distances
            at synchronized SGP4 ephemeris points. An object cannot be declared collision-clear without screening.
          </p>
        </div>

        <div className="rounded border border-cyan-500/20 bg-cyan-950/10 p-4">
          <div className="flex items-center gap-2 font-mono text-xs font-bold text-cyan-300">
            <Zap size={14} /> 2. OBSERVATIONAL CONFIDENCE (ACI)
          </div>
          <p className="mt-2 text-xs text-slate-300 leading-5">
            How trustworthy the current orbital elements are. High ACI = tight error bounds. Low ACI = high
            positional uncertainty that widens the collision probability envelope.
          </p>
        </div>
      </div>

      <div className="mission-grid">
        <div className="min-w-0 space-y-4">
          <ReliabilityContext />

          <Panel
            title="Objects Requiring Verification (Lowest ACI First)"
            eyebrow="PRIORITY SURVEILLANCE LIST"
            action={
              <div className="flex items-center gap-2">
                {["ALL", "Satellite", "Debris"].map((t) => (
                  <button
                    key={t}
                    onClick={() => setFilterType(t)}
                    className={`rounded px-2 py-0.5 font-mono text-[9px] font-medium transition-colors ${
                      filterType === t
                        ? "bg-cyan-400/20 text-cyan-200 border border-cyan-400/40"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {t.toUpperCase()}
                  </button>
                ))}
              </div>
            }
          >
            <DataState
              error={objects.isError}
              loading={objects.isLoading}
              retry={() => objects.refetch()}
            />

            <div data-testid="risk-object-list" className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left text-[11px]">
                <thead className="technical-label">
                  <tr>
                    {["Target Object", "ACI / Decision", "ML Reliability", "Age / Consistency", "Screening Status", "Action"].map(
                      (label) => (
                        <th key={label} className="px-3 pb-3 font-normal">
                          {label}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {!objects.isError ? (
                    objects.data?.objects.map((o) => {
                      const last = !history.isError
                        ? history.data?.items.find((h) => h.target_id === o.id)
                        : undefined;
                      const isSelected = selectedObjectId === o.id;

                      return (
                        <tr
                          key={o.id}
                          data-testid={`risk-object-${o.id}`}
                          className={`border-t border-slate-800/80 transition-colors ${
                            isSelected ? "bg-cyan-950/20" : "hover:bg-slate-900/30"
                          }`}
                        >
                          <td className="px-3 py-3">
                            <button
                              data-testid={`select-risk-object-${o.id}`}
                              onClick={() => setSelectedObject(o.id)}
                              className="text-left font-medium text-cyan-200 hover:underline"
                            >
                              {o.name || o.id}
                            </button>
                            <div className="mt-0.5 font-mono text-[8px] text-slate-500">
                              NORAD {o.id} · {o.type}
                            </div>
                          </td>

                          <td className="px-3">
                            <div className="font-mono font-bold text-slate-200">
                              {number(o.aci, 3)}
                            </div>
                            <div className="mt-1">
                              <StatusChip value={o.decision} />
                            </div>
                          </td>

                          <td className="px-3">
                            <div className="font-mono text-cyan-100">
                              {percent(o.model_confidence)}
                            </div>
                            <div className="mt-1">
                              <StatusChip value={o.ml_prediction} />
                            </div>
                          </td>

                          <td className="px-3 font-mono leading-5 text-slate-400">
                            <div>Age: {number(o.data_age_days, 1, " d")}</div>
                            <div>Arc: {number(o.trajectory_consistency, 3)}</div>
                          </td>

                          <td className="px-3">
                            <StatusChip value={last?.status || "NOT_SCREENED"} />
                            {last ? (
                              <Link
                                data-testid={`risk-history-${o.id}`}
                                to={`/conjunctions/history?screening=${last.screening_id}`}
                                className="mt-1 block font-mono text-[8px] text-slate-500 underline hover:text-slate-300"
                              >
                                Saved screening, not live
                              </Link>
                            ) : null}
                          </td>

                          <td className="px-3">
                            <Link
                              to={`/conjunctions?target=${o.id}`}
                              className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-1 font-mono text-[9px] text-cyan-200 transition-colors hover:bg-slate-700"
                            >
                              SCREEN <ArrowUpRight size={10} />
                            </Link>
                          </td>
                        </tr>
                      );
                    })
                  ) : null}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* Selected Object Intelligence Side Panel */}
        <ObjectIntelligence data={data} />
      </div>
    </div>
  );
}