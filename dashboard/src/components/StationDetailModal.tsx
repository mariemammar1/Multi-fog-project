import React, { useEffect } from 'react';
import {
  X,
  BatteryCharging,
  Zap,
  MapPin,
  Clock,
  Navigation,
  Compass,
  CheckCircle,
  Wifi,
} from 'lucide-react';
import { Station, TerritoryForecast, DriverLocation } from '../types';
import { calculateDistanceKm, estimateTravelTimeMin } from '../services/recommendationEngine';

interface StationDetailModalProps {
  isOpen: boolean;
  station: Station | null;
  onClose: () => void;
  forecast?: TerritoryForecast;
  driverLocation: DriverLocation;
  isDestinationActive?: boolean;
  onSetDestination: (station: Station) => void;
  onViewOnMap: (station: Station) => void;
}

export const StationDetailModal: React.FC<StationDetailModalProps> = ({
  isOpen,
  station,
  onClose,
  forecast,
  driverLocation,
  isDestinationActive = false,
  onSetDestination,
  onViewOnMap,
}) => {
  /* Escape key */
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen || !station) return null;

  const distanceKm = calculateDistanceKm(driverLocation.lat, driverLocation.lng, station.lat, station.lng);
  const travelTimeMin = estimateTravelTimeMin(distanceKm);
  const isFast = station.fastCount > 0;

  const availPct = station.totalPiles > 0
    ? Math.round((station.availablePiles / station.totalPiles) * 100)
    : 0;

  const occupancyLabel = forecast
    ? forecast.expectedOccupancyPercent < 40
      ? { text: 'Faible affluence', color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200' }
      : forecast.expectedOccupancyPercent < 70
      ? { text: 'Affluence modérée', color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' }
      : { text: 'Forte affluence', color: 'text-rose-600', bg: 'bg-rose-50 border-rose-200' }
    : null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      style={{ background: 'rgba(15,23,42,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Panel */}
      <div className="bg-white w-full sm:max-w-lg sm:rounded-3xl rounded-t-3xl max-h-[92vh] overflow-y-auto shadow-2xl relative animate-slideUp">

        {/* Drag handle on mobile */}
        <div className="sm:hidden flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-slate-200" />
        </div>

        {/* Header */}
        <div className="sticky top-0 bg-white/95 backdrop-blur-sm border-b border-slate-100 px-6 py-4 flex items-start justify-between gap-3 z-10">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-cyan-50 text-cyan-700 border border-cyan-200">
                {station.fogName}
              </span>
              {isDestinationActive && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <CheckCircle className="w-3 h-3" />
                  Destination Active
                </span>
              )}
            </div>
            <h3 className="text-xl font-black text-slate-900 leading-tight truncate">{station.name}</h3>
            <p className="text-xs text-slate-400 font-medium flex items-center gap-1 mt-0.5">
              <MapPin className="w-3.5 h-3.5 text-cyan-500" />
              Zone {station.district} · Station #{station.id}
            </p>
          </div>

          {/* Close button — always visible, large tap target */}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onClose(); }}
            aria-label="Fermer"
            className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">

          {/* Key metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-center">
              <div className="flex items-center justify-center gap-1.5 text-xs text-slate-500 font-bold mb-2">
                <Clock className="w-4 h-4 text-cyan-500" /> Temps de route
              </div>
              <div className="text-3xl font-black text-slate-900 leading-none">~{travelTimeMin}</div>
              <div className="text-xs text-slate-400 font-medium mt-1">{distanceKm} km depuis vous</div>
            </div>

            <div className={`rounded-2xl p-4 border text-center ${
              station.availablePiles > 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'
            }`}>
              <div className={`flex items-center justify-center gap-1.5 text-xs font-bold mb-2 ${
                station.availablePiles > 0 ? 'text-emerald-700' : 'text-rose-700'
              }`}>
                <BatteryCharging className={`w-4 h-4 ${station.availablePiles > 0 ? 'text-emerald-600' : 'text-rose-500'}`} />
                Bornes Libres
              </div>
              <div className={`text-3xl font-black leading-none ${station.availablePiles > 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
                {station.availablePiles}
              </div>
              <div className={`text-xs font-semibold mt-1 ${station.availablePiles > 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                / {station.totalPiles} · {availPct}% disponibles
              </div>
            </div>
          </div>

          {/* Tech specs */}
          <div className="bg-slate-50 rounded-2xl border border-slate-200 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-100/60">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Caractéristiques</span>
            </div>
            <div className="divide-y divide-slate-100">
              {[
                {
                  label: 'Type de charge',
                  value: isFast ? '⚡ DC Rapide + AC Standard' : 'AC Standard',
                  icon: <Zap className="w-4 h-4 text-amber-500" />,
                },
                {
                  label: 'Puissance maximale',
                  value: `${station.maxPowerKw} kW`,
                  icon: <Zap className="w-4 h-4 text-amber-500" />,
                  highlight: true,
                },
                {
                  label: 'Prises DC Rapide',
                  value: station.fastCount > 0 ? `${station.fastCount} prise${station.fastCount > 1 ? 's' : ''}` : 'Aucune',
                  icon: <BatteryCharging className="w-4 h-4 text-cyan-500" />,
                },
                {
                  label: 'Prises AC Standard',
                  value: station.slowCount > 0 ? `${station.slowCount} prise${station.slowCount > 1 ? 's' : ''}` : 'Aucune',
                  icon: <BatteryCharging className="w-4 h-4 text-slate-400" />,
                },
                {
                  label: 'Territoire Fog',
                  value: station.fogName,
                  icon: <Wifi className="w-4 h-4 text-cyan-500" />,
                },
              ].map(({ label, value, icon, highlight }) => (
                <div key={label} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                    {icon}
                    {label}
                  </div>
                  <span className={`text-xs font-bold ${highlight ? 'text-amber-700 text-sm' : 'text-slate-800'}`}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* AI forecast hint */}
          {forecast && occupancyLabel && (
            <div className={`flex items-start gap-3 p-3.5 rounded-2xl border text-xs ${occupancyLabel.bg}`}>
              <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${occupancyLabel.color.replace('text-', 'bg-')}`} />
              <div>
                <span className={`font-bold ${occupancyLabel.color}`}>{occupancyLabel.text} prévu</span>
                <span className="text-slate-500 ml-1">
                  dans le secteur {station.fogName} d'ici 1h ({forecast.expectedOccupancyPercent}% d'occupation prévue).
                </span>
                <p className="text-slate-400 mt-0.5">Prévision Chronos-2 au niveau du territoire, non spécifique à cette station.</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="px-6 pb-6 pt-2 flex flex-col sm:flex-row gap-2.5">
          <button
            type="button"
            onClick={() => { onSetDestination(station); onClose(); }}
            className="flex-1 flex items-center justify-center gap-2 py-4 px-5 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-sm shadow-glow-emerald transition-all cursor-pointer active:scale-[0.98]"
          >
            <Navigation className="w-4 h-4" />
            Choisir · Naviguer
          </button>

          <button
            type="button"
            onClick={() => { onViewOnMap(station); onClose(); }}
            className="flex-1 flex items-center justify-center gap-2 py-4 px-5 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-sm border border-slate-200 transition-colors cursor-pointer"
          >
            <Compass className="w-4 h-4" />
            Voir sur la carte
          </button>

          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onClose(); }}
            className="sm:w-auto px-5 py-4 rounded-2xl bg-white hover:bg-slate-50 text-slate-400 font-bold text-sm border border-slate-200 transition-colors cursor-pointer"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
};
