import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import type { ScreeningResult, ScreeningRow } from "@/lib/orbis";
import { number, utc } from "@/lib/data";
import { StatusChip } from "./ConsolePrimitives";

export function ScreeningRows({rows,prefix="screening"}:{rows:ScreeningRow[];prefix?:string}){return <div data-testid={`${prefix}-results-table`} className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-[11px]"><thead className="technical-label"><tr>{["Secondary object","Type","Minimum separation","TCA UTC","Status"].map(label=><th key={label} className="px-2 pb-3 font-normal">{label}</th>)}</tr></thead><tbody>{rows.map(row=><tr data-testid={`${prefix}-result-row-${row.object_id}`} key={row.object_id} className="border-t border-slate-800/80"><td className="max-w-44 px-2 py-3"><Link data-testid={`${prefix}-object-${row.object_id}`} to={`/objects/${row.object_id}`} className="text-cyan-200 hover:underline">{row.object_name||row.object_id}</Link><div className="mt-1 font-mono text-[8px] text-slate-500">{row.object_id}</div></td><td className="px-2 text-slate-400">{row.object_type}</td><td className="px-2 font-mono text-slate-200">{number(row.minimum_separation_km,3," km")}</td><td className="px-2 font-mono text-[9px] text-slate-400">{utc(row.tca_utc)}</td><td className="px-2"><StatusChip value={row.status}/></td></tr>)}</tbody></table></div>;}

export default function ScreeningResultView({result}:{result:ScreeningResult}){
  const methodId = result.method || "geometric_prototype";
  const methodDesc = result.method_description || "Geometric SGP4 separation screening. Computes minimum 3D Euclidean distance between propagated object positions. This is NOT a validated probability-of-collision (Pc) calculation. No covariance data is used. Results indicate geometric proximity only.";
  return (
    <div data-testid="screening-result">
      {/* ── Geometric-only warning banner ── */}
      <div
        data-testid="screening-method-warning"
        className="mb-4 flex items-start gap-3 border border-amber-400/30 bg-amber-400/[.06] px-4 py-3"
      >
        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-300" />
        <div className="min-w-0">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-amber-200">
            Geometric screening only — method:&nbsp;
            <span data-testid="screening-method-id" className="text-amber-100">{methodId}</span>
          </p>
          <p className="mt-1 text-[10px] leading-5 text-amber-200/80">
            <b className="text-amber-100">This is not a validated probability of collision (Pc).</b>
            &nbsp;Minimum separation in km&nbsp;<span className="font-bold">≠</span>&nbsp;collision probability.
            No covariance data is used; results reflect geometric proximity only.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <StatusChip value={result.status}/>
        <div data-testid="screening-result-summary" className="font-mono text-[9px] text-slate-400">
          {result.objects_screened?.toLocaleString()??"—"} SCREENED · {result.potential_count??"—"} POTENTIAL
        </div>
      </div>

      <div className="my-5 grid gap-3 sm:grid-cols-3">
        <div data-testid="screening-target-readout" className="border-l border-slate-700 pl-3">
          <div className="technical-label">TARGET</div>
          <div className="mt-2 text-xs text-slate-200">{result.target_name||result.target_id}</div>
        </div>
        <div data-testid="minimum-separation-readout" className="border-l border-cyan-400/40 pl-3">
          <div className="technical-label">MINIMUM SEPARATION</div>
          <div className="mt-2 font-mono text-lg text-cyan-100">{number(result.minimum_separation_km,3," km")}</div>
          <div className="mt-1 font-mono text-[8px] text-amber-400/70">NOT COLLISION PROBABILITY</div>
        </div>
        <div data-testid="tca-readout" className="border-l border-slate-700 pl-3">
          <div className="technical-label">TCA UTC</div>
          <div className="mt-2 font-mono text-[10px] text-slate-300">{utc(result.tca_utc)}</div>
        </div>
      </div>

      {result.error?<p data-testid="screening-backend-error" className="mb-4 text-xs text-red-300">{result.error}</p>:null}

      <ScreeningRows rows={result.results||[]}/>

      {/* ── Provenance / method footer ── */}
      <div data-testid="screening-result-provenance" className="mt-4 border-t border-slate-800 pt-3 font-mono text-[8px] leading-5 text-slate-500">
        <span className="text-slate-400">METHOD: </span>
        <span data-testid="screening-provenance-method" className="text-amber-400/80">{methodId}</span>
        <br/>
        {methodDesc}
        <br/>
        {result.disclaimer}
        <br/>
        ID {result.screening_id} · {utc(result.timestamp_utc)}
      </div>
    </div>
  );
}