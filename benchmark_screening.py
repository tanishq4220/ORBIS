"""
Independent screening benchmark script for ORBIS full catalog.
Executes geometric screening against all 18,689 objects in the active catalog.
"""
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from catalog import row_to_object, store
from screening import screen_object

def main():
    print("Loading catalog store...")
    t_load_start = time.perf_counter()
    store.load()
    t_load_end = time.perf_counter()
    print(f"Catalog loaded in {t_load_end - t_load_start:.3f}s. Total objects: {len(store.df)}")

    # Convert DataFrame rows using row_to_object exactly as server.py does
    rows = [row_to_object(r) for _, r in store.df.iterrows()]
    
    # Select target object: ISS (ZARYA) ID 25544 if available, or first row
    target_row = next((r for r in rows if str(r.get("id")) == "25544"), rows[0])
    target_id = str(target_row["id"])
    target_name = target_row.get("name", "TARGET")
    tle1 = target_row["tle_line1"]
    tle2 = target_row["tle_line2"]
    
    print(f"Target selected: NORAD {target_id} ({target_name})")
    print(f"Parameters: window_min=60, time_step_min=10, threshold_km=50.0")
    print("Running screening benchmark against full catalog...")
    
    t0 = time.perf_counter()
    result = screen_object(
        target_id=target_id,
        target_tle1=tle1,
        target_tle2=tle2,
        catalog_rows=rows,
        time_step_min=10,
        window_min=60,
        threshold_km=50.0
    )
    t1 = time.perf_counter()
    elapsed = t1 - t0
    
    print("=" * 60)
    print("INDEPENDENT FULL-CATALOG SCREENING BENCHMARK RESULTS (ISS 25544)")
    print("=" * 60)
    print(f"Screening Execution Time : {elapsed:.4f} seconds")
    print(f"Objects Evaluated        : {result['objects_screened']}")
    print(f"Conjunctions Detected    : {len(result['results'])}")
    print(f"Minimum Separation       : {result['minimum_separation_km']} km")
    print(f"Screening Method         : {result['method']}")
    print(f"Disclaimer               : {result['disclaimer']}")
    print("=" * 60)

    # Second benchmark: object 25867 with pytest parameters (window_min=90, time_step_min=15, threshold=75.0)
    target_row_2 = next((r for r in rows if str(r.get("id")) == "25867"), None)
    if target_row_2:
        print("\nRunning benchmark for object 25867 (parameters from test_tscheck_screening_history_immutable)...")
        t2_0 = time.perf_counter()
        result_2 = screen_object(
            target_id="25867",
            target_tle1=target_row_2["tle_line1"],
            target_tle2=target_row_2["tle_line2"],
            catalog_rows=rows,
            time_step_min=15,
            window_min=90,
            threshold_km=75.0,
            top_n=5
        )
        t2_1 = time.perf_counter()
        elapsed_2 = t2_1 - t2_0
        print("=" * 60)
        print("INDEPENDENT FULL-CATALOG SCREENING BENCHMARK RESULTS (OBJECT 25867)")
        print("=" * 60)
        print(f"Screening Execution Time : {elapsed_2:.4f} seconds")
        print(f"Objects Evaluated        : {result_2['objects_screened']}")
        print(f"Conjunctions Detected    : {len(result_2['results'])}")
        print(f"Minimum Separation       : {result_2['minimum_separation_km']} km")
        print(f"Screening Method         : {result_2['method']}")
        print("=" * 60)

if __name__ == "__main__":
    main()
