import React, { useState } from 'react';
import {
  Zap,
  MapPin,
  RefreshCw,
  Info,
  Navigation,
  Crosshair,
  X,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { DriverLocation, Station } from '../types';
import { PRESET_LOCATIONS } from '../services/recommendationEngine';
import { MultiFogStatus } from '../services/api';

interface HeaderProps {
  systemStatus: MultiFogStatus;
  currentLocation: DriverLocation;
  onLocationChange: (loc: DriverLocation) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenDataProvenance: () => void;
  onToggleFilters: () => void;
  filtersOpen: boolean;
  activeFogCount: number;
  activeDestination: Station | null;
  onClearDestination: () => void;
  onViewDestination: () => void;
  onShowToast: (title: string, message?: string, type?: 'success' | 'info' | 'warning') => void;
}

export const Header: React.FC<HeaderProps> = ({
  systemStatus,
  currentLocation,
  onLocationChange,
  onRefresh,
  isRefreshing,
  onOpenDataProvenance,
  activeFogCount,
  activeDestination,
  onClearDestination,
  onViewDestination,
  onShowToast,
}) => {
  const [gpsLoading, setGpsLoading] = useState(false);

  const handleRequestGps = () => {
    if (!navigator.geolocation) {
      onShowToast('GPS Indisponible', 'Votre navigateur ne supporte pas la géolocalisation.', 'warning');
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGpsLoading(false);
        const newLoc: DriverLocation = {
          label: 'Position GPS Réelle',
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          district: 'GPS Utilisateur',
          isCustomGps: true,
        };
        onLocationChange(newLoc);
        onShowToast('Position GPS Détectée', `${newLoc.lat.toFixed(4)}, ${newLoc.lng.toFixed(4)}`, 'success');
      },
      () => {
        setGpsLoading(false);
        onShowToast('Signal GPS Inaccessible', 'Position réinitialisée sur Nanshan Tech Park.', 'warning');
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const isLive = systemStatus.isLive;

  return (
    <header className="sticky top-0 z-40 bg-white/85 backdrop-blur-xl border-b border-slate-200/70 shadow-[0_1px_12px_rgba(0,0,0,0.05)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-[68px] gap-3">

          {/* ── Brand ── */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center shadow-glow-cyan flex-shrink-0">
              <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <div className="hidden sm:block">
              <div className="flex items-baseline gap-2">
                <span className="text-[17px] font-black tracking-tight text-slate-900 leading-none">
                  EV&nbsp;<span className="gradient-text">Guide</span>
                </span>
                <span className="text-[9px] font-extrabold tracking-widest uppercase text-slate-400 leading-none pb-0.5">
                  Multi-Fog
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium leading-tight mt-0.5">
                Assistant de recharge intelligent
              </p>
            </div>
          </div>

          {/* ── Active Destination Pill ── */}
          {activeDestination && (
            <div className="hidden lg:flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-emerald-50 border border-emerald-200 shadow-sm animate-fadeIn flex-shrink-0">
              <Navigation className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
              <div className="leading-tight">
                <span className="block text-[9px] font-bold uppercase tracking-widest text-emerald-500">Destination</span>
                <strong className="text-[12px] text-slate-900 font-extrabold truncate max-w-[150px] block">
                  {activeDestination.name}
                </strong>
              </div>
              <button
                onClick={onViewDestination}
                className="ml-1 px-2.5 py-1 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-bold transition-colors cursor-pointer"
              >
                Carte
              </button>
              <button
                onClick={onClearDestination}
                className="p-1 rounded-full text-slate-400 hover:text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer"
                title="Annuler"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* ── Right Controls ── */}
          <div className="flex items-center gap-2 ml-auto">

            {/* Location Selector */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-2xl px-3 py-1.5 gap-2 hover:border-slate-300 transition-colors">
              <MapPin className="w-3.5 h-3.5 text-cyan-500 flex-shrink-0" />
              <div>
                <label className="block text-[9px] font-bold uppercase tracking-widest text-slate-400 leading-none mb-0.5">
                  Départ
                </label>
                <select
                  value={currentLocation.label}
                  onChange={(e) => {
                    const found = PRESET_LOCATIONS.find((loc) => loc.label === e.target.value);
                    if (found) {
                      onLocationChange(found);
                      onShowToast('Position mise à jour', found.label, 'info');
                    }
                  }}
                  aria-label="Position de départ"
                  className="bg-transparent text-[12px] font-bold text-slate-800 focus:outline-none cursor-pointer leading-none max-w-[130px] sm:max-w-none"
                >
                  {PRESET_LOCATIONS.map((loc) => (
                    <option key={loc.label} value={loc.label} className="bg-white text-slate-800">
                      {loc.label}
                    </option>
                  ))}
                  {currentLocation.isCustomGps && (
                    <option value={currentLocation.label} className="bg-white text-slate-800">
                      📍 GPS Utilisateur
                    </option>
                  )}
                </select>
              </div>
              <button
                onClick={handleRequestGps}
                disabled={gpsLoading}
                title="GPS réel"
                className="p-1 rounded-lg bg-white hover:bg-cyan-50 text-slate-500 hover:text-cyan-600 border border-slate-200 transition-colors disabled:opacity-50 cursor-pointer"
              >
                <Crosshair className={`w-3.5 h-3.5 ${gpsLoading ? 'animate-spin text-cyan-600' : ''}`} />
              </button>
            </div>

            {/* Live Status Badge */}
            <div className="hidden xl:flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-slate-50 border border-slate-200 text-[11px] font-semibold">
              <span className="relative flex h-2 w-2 flex-shrink-0">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${isLive ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${isLive ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              </span>
              {isLive ? (
                <Wifi className="w-3 h-3 text-emerald-600" />
              ) : (
                <WifiOff className="w-3 h-3 text-amber-500" />
              )}
              <span className="text-slate-600">{activeFogCount}/3 Fogs</span>
              <span className="text-slate-300">·</span>
              <span className="text-cyan-700 font-bold">Chronos-2</span>
            </div>

            {/* Refresh */}
            <button
              onClick={() => {
                onRefresh();
                onShowToast('Données Actualisées', 'Synchronisation avec les Fog Nodes.', 'success');
              }}
              disabled={isRefreshing}
              title="Actualiser"
              aria-label="Actualiser les données"
              className="p-2.5 rounded-2xl bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 transition-all disabled:opacity-50 cursor-pointer hover:border-slate-300"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-600' : ''}`} />
            </button>

            {/* Info */}
            <button
              onClick={onOpenDataProvenance}
              title="Transparence des données"
              aria-label="Informations"
              className="p-2.5 rounded-2xl bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-cyan-700 border border-slate-200 transition-all cursor-pointer hover:border-slate-300"
            >
              <Info className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
