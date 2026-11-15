"""
CLI Runner for the Multi-Fog EV Real-Time Simulation Engine.
Can run automated real-time simulation ticks with live console output,
or serve as an interactive test runner.
"""

import argparse
import time
from simulator.realtime_engine import engine


def main():
    parser = argparse.ArgumentParser(description="Multi-Fog EV Real-Time Simulator Runner")
    parser.add_argument("--scenario", default="S1_NORMAL", choices=["S1_NORMAL", "S2_COOPERATION", "S6_SATURATION", "S7_ML_REACTIVE"], help="Active simulation scenario")
    parser.add_argument("--ticks", type=int, default=10, help="Number of ticks to run (0 for infinite loop)")
    parser.add_argument("--interval", type=float, default=1.5, help="Seconds between ticks")
    parser.add_argument("--inject-fog", choices=["fog-a", "fog-b", "fog-c"], help="Fog to inject surge traffic into")
    parser.add_argument("--inject-count", type=int, default=20, help="Number of vehicles to inject")
    parser.add_argument("--reset", action="store_true", help="Reset all databases before starting")

    args = parser.parse_args()

    if args.reset:
        print("[*] Reinitialisation des bases SQLite...")
        engine.reset_databases()

    engine.scenario = args.scenario
    print("=" * 65)
    print(f"   MULTI-FOG EV REAL-TIME SIMULATOR — MODE : {args.scenario}")
    print("=" * 65)

    if args.inject_fog:
        print(f"[*] Injection de +{args.inject_count} EV sur {args.inject_fog.upper()}...")
        engine.inject_traffic(args.inject_fog, args.inject_count)

    count = 0
    try:
        while args.ticks == 0 or count < args.ticks:
            count += 1
            engine.step()
            status = engine.get_status()

            print(f"\n--- TICK #{status['tick']} [Scenario: {status['scenario']}] ---")
            caps = status["capacities"]
            for fog_id, c in caps.items():
                print(f"  {fog_id.upper()}: {c['occupied_piles']}/{c['total_piles']} occupées ({c['occupancy_percent']}%) | Libres: {c['available_piles']} | Puissance dispo: {c['available_power_kw']} kW")

            print(f"  Cumul: Arrivées={status['total_arrivals']} | Actives={status['active_sessions_count']} | Terminées={status['total_completed']} | Coop V7={status['total_cooperations']} | Non servis={status['total_unserved']}")

            if status["recent_events"]:
                latest = status["recent_events"][0]
                print(f"  Dernier événement: [{latest['category']}] {latest['title']} - {latest['message']}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[!] Simulation interrompue par l'utilisateur.")

    print("\n[OK] Fin de la session de simulation.")


if __name__ == "__main__":
    main()
