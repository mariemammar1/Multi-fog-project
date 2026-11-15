import React, { useState, useEffect } from 'react';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Zap,
  Activity,
  Layers,
  ArrowRight,
  ShieldAlert,
  CheckCircle,
  AlertTriangle,
  Clock,
  BatteryCharging,
  Cpu,
  Flame,
  Radio
} from 'lucide-react';
import {
  FogId,
  FogCapacity,
  SimulatorStatus,
  SimulatorScenario,
  TerritoryMeta
} from '../types';
import { FogDataService } from '../services/api';

interface RealTimeSimulatorProps {
  capacities: Record<FogId, FogCapacity>;
  territoriesMeta: Record<FogId, TerritoryMeta>;
  onRefreshData: () => void;
  onShowToast: (title: string, message?: string, type?: 'success' | 'info' | 'warning') => void;
}

export const RealTimeSimulator: React.FC<RealTimeSimulatorProps> = ({
  capacities,
  territoriesMeta,
  onRefreshData,
  onShowToast
}) => {
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [speed, setSpeed] = useState<number>(2.0); // seconds per tick
  const [isBusy, setIsBusy] = useState<boolean>(false);

  useEffect(() => {
    // Initial fetch
    FogDataService.getSimulatorStatus().then(setStatus);

    // Subscribe to updates
    const unsubscribe = FogDataService.onSimulatorUpdate((newStatus) => {
      setStatus(newStatus);
      onRefreshData();
    });

    return () => {
      unsubscribe();
    };
  }, [onRefreshData]);

  const handleStart = async () => {
    setIsBusy(true);
    const newStatus = await FogDataService.startSimulator(speed);
    setStatus(newStatus);
    setIsBusy(false);
    onShowToast('Simulateur Démarré', 'La simulation temps réel tourne en boucle continue.', 'success');
  };

  const handleStop = async () => {
    setIsBusy(true);
    const newStatus = await FogDataService.stopSimulator();
    setStatus(newStatus);
    setIsBusy(false);
    onShowToast('Simulateur en Pause', 'Simulation suspendue.', 'info');
  };

  const handleStep = async () => {
    setIsBusy(true);
    const newStatus = await FogDataService.stepSimulator();
    setStatus(newStatus);
    setIsBusy(false);
    onRefreshData();
  };

  const handleReset = async () => {
    setIsBusy(true);
    const newStatus = await FogDataService.resetSimulator();
    setStatus(newStatus);
    setIsBusy(false);
    onRefreshData();
    onShowToast('Bases Réinitialisées', 'Toutes les bornes ont été remises à l\'état disponible.', 'info');
  };

  const handleScenarioChange = async (sc: SimulatorScenario) => {
    setIsBusy(true);
    const newStatus = await FogDataService.setSimulatorScenario(sc);
    setStatus(newStatus);
    setIsBusy(false);
    const names: Record<SimulatorScenario, string> = {
      S1_NORMAL: 'Scénario 1 : Fonctionnement Normal',
      S2_COOPERATION: 'Scénario 2-4 : Coopération V7',
      S6_SATURATION: 'Scénario 6 : Saturation Totale',
      S7_ML_REACTIVE: 'Scénario 7 : Prédiction ML & Réactivité',
    };
    onShowToast('Scénario Modifié', names[sc], 'info');
  };

  const handleInject = async (fogId: FogId, count: number) => {
    setIsBusy(true);
    const newStatus = await FogDataService.injectSimulatorTraffic(fogId, count);
    setStatus(newStatus);
    setIsBusy(false);
    onRefreshData();
    onShowToast('Pic de Demande Injecté', `+${count} véhicules ajoutés sur ${fogId.toUpperCase()}.`, 'warning');
  };

  const currentCapacities = status?.capacities || capacities;
  const isRunning = status?.is_running ?? false;
  const tick = status?.tick ?? 0;
  const scenario = status?.scenario ?? 'S1_NORMAL';

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* ── Top Bar: Control Center ── */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl border border-indigo-800/40 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                <Radio className={`w-6 h-6 ${isRunning ? 'animate-pulse text-cyan-300' : ''}`} />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-xl sm:text-2xl font-black tracking-tight text-white">
                    Simulateur Réseau Temps Réel
                  </h2>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase inline-flex items-center gap-1.5 ${
                      isRunning
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'}`}></span>
                    {isRunning ? 'Simulation Active' : 'En Pause'}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-slate-300 font-medium mt-0.5">
                  Génération dynamique de flux de véhicules, sessions SQLite réelles et négociation inter-fog V7.
                </p>
              </div>
            </div>
          </div>

          {/* Action buttons & Tick badge */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="bg-white/10 backdrop-blur-md px-4 py-2 rounded-2xl border border-white/10 flex items-center gap-2.5">
              <Clock className="w-4 h-4 text-cyan-300" />
              <div className="text-left">
                <div className="text-[10px] uppercase font-bold text-slate-300 tracking-wider">Tick d'horloge</div>
                <div className="text-base font-black text-cyan-300">#{tick}</div>
              </div>
            </div>

            {/* Play / Pause */}
            {isRunning ? (
              <button
                onClick={handleStop}
                disabled={isBusy}
                className="flex items-center gap-2 px-5 py-2.5 rounded-2xl font-black text-sm bg-amber-500 hover:bg-amber-400 text-slate-950 transition-all shadow-lg shadow-amber-500/20 cursor-pointer active:scale-95"
              >
                <Pause className="w-4 h-4" />
                <span>Pause</span>
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={isBusy}
                className="flex items-center gap-2 px-5 py-2.5 rounded-2xl font-black text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition-all shadow-lg shadow-emerald-500/20 cursor-pointer active:scale-95"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Démarrer</span>
              </button>
            )}

            {/* Step */}
            <button
              onClick={handleStep}
              disabled={isBusy || isRunning}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl font-black text-sm transition-all border ${
                isRunning
                  ? 'bg-white/5 border-white/10 text-slate-500 cursor-not-allowed'
                  : 'bg-white/10 hover:bg-white/20 border-white/20 text-white cursor-pointer active:scale-95'
              }`}
              title="Avancer manuellement d'un pas"
            >
              <SkipForward className="w-4 h-4" />
              <span className="hidden sm:inline">Pas +1</span>
            </button>

            {/* Reset */}
            <button
              onClick={handleReset}
              disabled={isBusy}
              className="flex items-center gap-2 px-3.5 py-2.5 rounded-2xl font-bold text-sm bg-white/10 hover:bg-rose-500/20 hover:text-rose-300 hover:border-rose-500/40 border border-white/15 text-slate-300 transition-all cursor-pointer active:scale-95"
              title="Remettre les bornes à disponible"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Speed selector */}
            <div className="flex bg-white/10 rounded-xl p-1 border border-white/10 text-xs font-bold">
              {[
                { label: '1x (2s)', val: 2.0 },
                { label: '2x (1s)', val: 1.0 },
                { label: '4x (0.5s)', val: 0.5 },
              ].map((s) => (
                <button
                  key={s.val}
                  onClick={() => {
                    setSpeed(s.val);
                    if (isRunning) FogDataService.startSimulator(s.val);
                  }}
                  className={`px-2.5 py-1 rounded-lg transition-colors cursor-pointer ${
                    speed === s.val ? 'bg-cyan-500 text-slate-950 font-black' : 'text-slate-300 hover:text-white'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Scenario Selection Bar ── */}
        <div className="mt-8 pt-6 border-t border-white/10">
          <div className="text-xs font-black uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Sélectionner le Scénario Actif</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              {
                id: 'S1_NORMAL' as SimulatorScenario,
                badge: 'Scénario 1',
                title: 'Normal (Autonome)',
                desc: 'Flux régulier. 100% géré localement. Zéro inter-fog.',
                color: 'emerald',
                activeBg: 'bg-emerald-500/20 border-emerald-400 text-emerald-200',
              },
              {
                id: 'S2_COOPERATION' as SimulatorScenario,
                badge: 'Scénarios 2 à 4',
                title: 'Coopération V7',
                desc: 'Pic Fog B saturé ➜ HOLD ➜ CONFIRM ➜ ACTIVATE sur Fog A.',
                color: 'amber',
                activeBg: 'bg-amber-500/20 border-amber-400 text-amber-200',
              },
              {
                id: 'S6_SATURATION' as SimulatorScenario,
                badge: 'Scénario 6',
                title: 'Saturation Globale',
                desc: 'Tous Fogs à 100%. DECLINE ➜ 0 recharge fictive.',
                color: 'rose',
                activeBg: 'bg-rose-500/20 border-rose-400 text-rose-200',
              },
              {
                id: 'S7_ML_REACTIVE' as SimulatorScenario,
                badge: 'Scénario 7',
                title: 'ML vs Réel',
                desc: 'Prévision Chronos-2 sans réservation préalable ➜ Réactif.',
                color: 'sky',
                activeBg: 'bg-sky-500/20 border-sky-400 text-sky-200',
              },
            ].map((sc) => {
              const isSelected = scenario === sc.id;
              return (
                <button
                  key={sc.id}
                  onClick={() => handleScenarioChange(sc.id)}
                  className={`text-left p-4 rounded-2xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? `${sc.activeBg} shadow-lg ring-2 ring-white/20`
                      : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/10 text-white">
                      {sc.badge}
                    </span>
                    {isSelected && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                  </div>
                  <div className="font-bold text-sm text-white">{sc.title}</div>
                  <div className="text-xs text-slate-400 mt-1 leading-snug">{sc.desc}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Real-Time Metrics & Fog Gauges ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {(['fog-a', 'fog-b', 'fog-c'] as FogId[]).map((fogId) => {
          const cap = currentCapacities[fogId] || {
            total_piles: 6000,
            available_piles: 4500,
            occupied_piles: 1500,
            available_power_kw: 80000,
          };
          const meta = territoriesMeta[fogId] || { name: fogId.toUpperCase(), color: '#06b6d4' };
          const pct = Math.min(100, Math.round(((cap.occupied_piles || 0) / (cap.total_piles || 1)) * 100));

          let badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
          let statusText = 'Normal';
          if (pct > 90) {
            badgeColor = 'bg-rose-50 text-rose-700 border-rose-200';
            statusText = 'Saturé (100%)';
          } else if (pct > 60) {
            badgeColor = 'bg-amber-50 text-amber-700 border-amber-200';
            statusText = 'Forte Demande';
          }

          return (
            <div
              key={fogId}
              className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                    {fogId.toUpperCase()}
                  </span>
                  <h3 className="text-base font-black text-slate-900 mt-1">{meta.name}</h3>
                </div>
                <span className={`text-xs font-black px-2.5 py-1 rounded-full border ${badgeColor}`}>
                  {statusText}
                </span>
              </div>

              {/* Progress bar */}
              <div className="space-y-1.5 mb-4">
                <div className="flex justify-between text-xs font-bold text-slate-600">
                  <span>Occupation Réelle</span>
                  <span className="text-slate-900 font-black">{pct}%</span>
                </div>
                <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden p-0.5">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      pct > 90
                        ? 'bg-rose-500'
                        : pct > 60
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${pct}%` }}
                  ></div>
                </div>
              </div>

              {/* Counts grid */}
              <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-slate-100">
                <div className="bg-slate-50 p-2.5 rounded-xl">
                  <div className="text-slate-500 font-medium">Bornes Libres</div>
                  <div className="text-base font-black text-emerald-600">
                    {(cap.available_piles || 0).toLocaleString()}
                  </div>
                </div>
                <div className="bg-slate-50 p-2.5 rounded-xl">
                  <div className="text-slate-500 font-medium">Occupées</div>
                  <div className="text-base font-black text-slate-900">
                    {(cap.occupied_piles || 0).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Quick Injection for this Fog */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500">Injecter trafic :</span>
                <div className="flex gap-1.5">
                  {[10, 25, 50].map((n) => (
                    <button
                      key={n}
                      onClick={() => handleInject(fogId, n)}
                      disabled={isBusy}
                      className="px-2 py-1 rounded-lg text-[11px] font-black bg-slate-100 hover:bg-cyan-50 hover:text-cyan-700 hover:border-cyan-200 border border-transparent transition-colors cursor-pointer"
                    >
                      +{n} EV
                    </button>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Network Global KPIs ── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
        {[
          { label: 'Total Arrivées', val: status?.total_arrivals ?? 0, icon: BatteryCharging, color: 'text-indigo-600 bg-indigo-50 border-indigo-100' },
          { label: 'Sessions Actives', val: status?.active_sessions_count ?? 0, icon: Zap, color: 'text-cyan-600 bg-cyan-50 border-cyan-100' },
          { label: 'Recharges Terminées', val: status?.total_completed ?? 0, icon: CheckCircle, color: 'text-emerald-600 bg-emerald-50 border-emerald-100' },
          { label: 'Coopération V7 (Transfers)', val: status?.total_cooperations ?? 0, icon: ArrowRight, color: 'text-amber-600 bg-amber-50 border-amber-100' },
          { label: 'Véhicules Non Servis', val: status?.total_unserved ?? 0, icon: AlertTriangle, color: 'text-rose-600 bg-rose-50 border-rose-100' },
        ].map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className={`p-4 rounded-2xl border ${kpi.color} flex flex-col justify-between`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-slate-600">{kpi.label}</span>
                <Icon className="w-4 h-4 opacity-75" />
              </div>
              <div className="text-xl sm:text-2xl font-black text-slate-900">{kpi.val.toLocaleString()}</div>
            </div>
          );
        })}
      </div>

      {/* ── Live Transaction Log ── */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/80 shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-indigo-600" />
            <h3 className="font-black text-slate-900 text-base sm:text-lg">
              Journal des Événements & Coopération en Temps Réel
            </h3>
          </div>
          <span className="text-xs font-bold text-slate-500">
            {status?.recent_events?.length || 0} événements récents
          </span>
        </div>

        {status?.recent_events && status.recent_events.length > 0 ? (
          <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
            {status.recent_events.map((evt) => {
              let badgeColor = 'bg-slate-100 text-slate-700 border-slate-200';
              if (evt.level === 'success') badgeColor = 'bg-emerald-50 text-emerald-800 border-emerald-200';
              if (evt.level === 'warning') badgeColor = 'bg-amber-50 text-amber-800 border-amber-200';
              if (evt.level === 'error') badgeColor = 'bg-rose-50 text-rose-800 border-rose-200';

              return (
                <div
                  key={evt.id}
                  className="flex items-start gap-3 p-3.5 rounded-2xl border border-slate-100 hover:border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors text-xs"
                >
                  <div className="text-slate-600 font-mono text-[11px] font-bold mt-0.5 whitespace-nowrap">
                    {evt.time}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-black border uppercase tracking-wider whitespace-nowrap ${badgeColor}`}>
                    {evt.category}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-black text-slate-900">{evt.title}</div>
                    <div className="text-slate-600 mt-0.5 leading-snug">{evt.message}</div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-10 text-slate-600 text-sm font-medium">
            Aucun événement enregistré. Cliquez sur <strong className="text-slate-700 font-semibold">Démarrer</strong> ou{' '}
            <strong className="text-slate-700 font-semibold">Pas +1</strong> pour lancer les premières arrivées de véhicules.
          </div>
        )}
      </div>
    </div>
  );
};
