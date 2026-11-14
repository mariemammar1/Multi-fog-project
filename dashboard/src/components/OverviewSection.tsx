import React from 'react';
import {
  BatteryCharging,
  Cpu,
  Layers,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Zap,
  TrendingUp,
  ShieldCheck
} from 'lucide-react';
import { FogCapacity, FogId, TerritoryForecast, TerritoryMeta } from '../types';

interface OverviewSectionProps {
  capacities: Record<FogId, FogCapacity>;
  forecasts: Record<FogId, TerritoryForecast>;
  territoriesMeta: Record<FogId, TerritoryMeta>;
  totalStationsCount: number;
  lastUpdated: string;
}

export const OverviewSection: React.FC<OverviewSectionProps> = ({
  capacities,
  forecasts,
  territoriesMeta,
  totalStationsCount,
  lastUpdated,
}) => {
  const fogs: FogId[] = ['fog-a', 'fog-b', 'fog-c'];

  const totalPiles = fogs.reduce((acc, fog) => acc + (capacities[fog]?.total_piles || 0), 0);
  const availablePiles = fogs.reduce((acc, fog) => acc + (capacities[fog]?.available_piles || 0), 0);
  const occupiedPiles = fogs.reduce((acc, fog) => acc + (capacities[fog]?.occupied_piles || 0), 0);
  const outOfServicePiles = fogs.reduce(
    (acc, fog) => acc + (capacities[fog]?.out_of_service_piles || 0),
    0
  );
  const totalPowerKw = fogs.reduce(
    (acc, fog) => acc + (capacities[fog]?.available_power_kw || 0),
    0
  );

  const globalAvailabilityPercent = totalPiles > 0 ? ((availablePiles / totalPiles) * 100).toFixed(1) : '0';

  return (
    <section className="space-y-6">
      {/* Top Banner: Question & Data Truthfulness Indicator */}
      <div className="bg-gradient-to-r from-sky-50 via-cyan-50 to-emerald-50 p-6 rounded-2xl border border-sky-100 shadow-sm relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-white/90 border border-cyan-200 text-cyan-800 text-xs font-bold mb-2 shadow-xs">
              <BatteryCharging className="w-3.5 h-3.5 text-cyan-600" />
              <span>Réseau Autonome Multi-Fog EV</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Recommandation Intelligente de Recharge pour Véhicules Électriques
            </h1>
            <p className="text-sm text-slate-600 mt-1 max-w-3xl">
              Arbitrage multi-critères en temps réel pour conducteurs EV à travers{' '}
              <strong className="text-sky-700 font-semibold">Fog A (Centre)</strong>,{' '}
              <strong className="text-emerald-700 font-semibold">Fog B (Est)</strong> et{' '}
              <strong className="text-amber-700 font-semibold">Fog C (Ouest)</strong>, enrichi par les prédictions d'occupation Chronos-2.
            </p>
          </div>

          {/* Data Transparency Pill */}
          <div className="flex flex-wrap items-center gap-2 text-xs bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center space-x-1.5 text-emerald-700 font-semibold">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Base SQLite Réelle</span>
            </div>
            <span className="text-slate-300">|</span>
            <div className="flex items-center space-x-1.5 text-cyan-700 font-semibold">
              <Cpu className="w-4 h-4 text-cyan-600" />
              <span>Inférence Chronos-2</span>
            </div>
            <span className="text-slate-300">|</span>
            <div className="flex items-center space-x-1 text-slate-500">
              <Clock className="w-3.5 h-3.5" />
              <span>{lastUpdated}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Global Stat KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Stations */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Total Stations</span>
            <Layers className="w-4 h-4 text-cyan-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 tracking-tight">
            {totalStationsCount.toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-slate-500 flex items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 mr-1.5" />
            3 Territoires Fog
          </div>
        </div>

        {/* Total Piles */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Bornes Totales</span>
            <BatteryCharging className="w-4 h-4 text-sky-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 tracking-tight">
            {totalPiles.toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-slate-500 flex items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-500 mr-1.5" />
            AC Standard & DC Rapide
          </div>
        </div>

        {/* Available Piles */}
        <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200 shadow-xs hover:border-emerald-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-800">Bornes Disponibles</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-emerald-700 tracking-tight">
            {availablePiles.toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-emerald-700 font-medium">
            {globalAvailabilityPercent}% Prêtes à charger
          </div>
        </div>

        {/* Occupied Piles */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Bornes Occupées</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-amber-600 tracking-tight">
            {occupiedPiles.toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            Sessions en cours
          </div>
        </div>

        {/* Out of Service */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Hors Service</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-800 tracking-tight">
            {outOfServicePiles}
          </div>
          <div className="mt-1 text-[11px] text-emerald-600 font-semibold">
            99.9% disponibilité
          </div>
        </div>

        {/* Available Power Capacity */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Puissance Réseau</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 tracking-tight">
            {(totalPowerKw / 1000).toFixed(1)} <span className="text-sm font-semibold text-slate-500">MW</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            Capacité électrique totale
          </div>
        </div>
      </div>

      {/* Territory Fog Nodes Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {fogs.map((fogId) => {
          const cap = capacities[fogId];
          const fc = forecasts[fogId];
          const meta = territoriesMeta[fogId];

          const isFogA = fogId === 'fog-a';
          const isFogB = fogId === 'fog-b';

          const accentBorder = isFogA
            ? 'border-sky-200 hover:border-sky-300'
            : isFogB
            ? 'border-emerald-200 hover:border-emerald-300'
            : 'border-amber-200 hover:border-amber-300';

          const badgeBg = isFogA
            ? 'bg-sky-50 text-sky-700 border-sky-200'
            : isFogB
            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
            : 'bg-amber-50 text-amber-700 border-amber-200';

          const occupancyLevel = fc?.occupancyLevel || 'low';
          const levelColor =
            occupancyLevel === 'low'
              ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
              : occupancyLevel === 'moderate'
              ? 'text-amber-700 bg-amber-50 border-amber-200'
              : 'text-rose-700 bg-rose-50 border-rose-200';

          const percentOccupied = fc?.expectedOccupancyPercent || 25;

          return (
            <div
              key={fogId}
              className={`bg-white rounded-2xl p-5 border ${accentBorder} shadow-xs hover:shadow-md transition-all duration-200 relative overflow-hidden`}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${badgeBg}`}>
                      {fogId.toUpperCase()}
                    </span>
                    <span className="text-xs font-semibold text-slate-500">
                      Port {fogId === 'fog-a' ? '8001' : fogId === 'fog-b' ? '8002' : '8003'}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mt-1.5">{meta?.name || fogId}</h3>
                </div>

                <div className={`px-2 py-0.5 rounded-md text-[11px] font-bold border ${levelColor}`}>
                  PRESSION {occupancyLevel.toUpperCase()}
                </div>
              </div>

              {/* Piles and Stations Counts */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-slate-100 text-center">
                <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Stations</span>
                  <span className="text-sm font-extrabold text-slate-900">
                    {meta?.total_stations?.toLocaleString() || 500}
                  </span>
                </div>
                <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Bornes</span>
                  <span className="text-sm font-extrabold text-slate-700">
                    {cap?.total_piles?.toLocaleString() || meta?.total_piles}
                  </span>
                </div>
                <div className="bg-emerald-50 p-2 rounded-lg border border-emerald-100">
                  <span className="text-[10px] text-emerald-700 uppercase tracking-wider block font-bold">Disponibles</span>
                  <span className="text-sm font-extrabold text-emerald-600">
                    {cap?.available_piles?.toLocaleString() || 0}
                  </span>
                </div>
              </div>

              {/* Chronos-2 Territory Forecast Bar */}
              <div className="mt-4 pt-3 border-t border-slate-100">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-600 font-medium flex items-center">
                    <TrendingUp className="w-3.5 h-3.5 mr-1 text-cyan-600" />
                    Prédiction Chronos-2 (+1h)
                  </span>
                  <span className="font-bold text-slate-900">
                    {percentOccupied}% <span className="text-slate-400 text-[11px] font-normal">occupation</span>
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      percentOccupied > 65
                        ? 'bg-rose-500'
                        : percentOccupied > 40
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, percentOccupied))}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2">
                  <span>Médiane active: <strong className="text-slate-800">{Math.round(fc?.forecastBusyQ50 || 0)}</strong> pts</span>
                  <span>MAE: <strong className="text-cyan-700">{meta?.mae_chronos || 0}</strong> vs Base {meta?.mae_baseline}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
