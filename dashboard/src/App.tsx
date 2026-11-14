import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Sparkles,
  Compass,
  Cpu,
  CheckCircle,
  AlertCircle,
  Info,
  X,
} from 'lucide-react';

import {
  Station,
  FogId,
  FogCapacity,
  TerritoryForecast,
  DriverLocation,
  ScoringWeights,
  UserPreferences,
  Recommendation,
  ToastMessage
} from './types';

import { FogDataService, MultiFogStatus } from './services/api';
import {
  rankStations,
  PRESET_LOCATIONS
} from './services/recommendationEngine';

import { Header } from './components/Header';
import { OverviewSection } from './components/OverviewSection';
import { RecommendationSection } from './components/RecommendationSection';
import { StationMap } from './components/StationMap';
import { ForecastSection } from './components/ForecastSection';
import { StationDetailModal } from './components/StationDetailModal';
import { DataProvenanceModal } from './components/DataProvenanceModal';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  // Static Dataset & Benchmarks
  const allStations = useMemo(() => FogDataService.getStations(), []);
  const territoriesMeta = useMemo(() => FogDataService.getTerritoriesMeta(), []);
  const evaluationData = useMemo(() => FogDataService.getEvaluationResults(), []);
  const historicalOccupancy = useMemo(() => FogDataService.getHistoricalOccupancy(), []);

  // System & Telemetry State
  const [capacities, setCapacities] = useState<Record<FogId, FogCapacity>>({} as any);
  const [forecasts, setForecasts] = useState<Record<FogId, TerritoryForecast>>({} as any);
  const [systemStatus, setSystemStatus] = useState<MultiFogStatus>({
    isLive: false,
    activeFogs: [],
    chronosLive: false,
    lastUpdated: 'Initialisation...',
  });
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // User & Driver State
  const [driverLocation, setDriverLocation] = useState<DriverLocation>(PRESET_LOCATIONS[0]);
  const [activeDestination, setActiveDestination] = useState<Station | null>(null);
  const [weights, setWeights] = useState<ScoringWeights>({
    travelTime: 0.45,
    predictedOccupancy: 0.35,
    waitingTime: 0.20,
  });
  const [preferences, setPreferences] = useState<UserPreferences>({
    vehicleType: 'ALL',
    minPowerKw: 0,
    maxDistanceKm: 25,
    selectedFog: 'ALL',
    onlyAvailable: true,
  });

  // Navigation, Selection & Modals
  const [activeTab, setActiveTab] = useState<'recommendations' | 'map' | 'forecasts'>('recommendations');
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState<boolean>(false);
  const [isDataProvenanceOpen, setIsDataProvenanceOpen] = useState<boolean>(false);
  const [filtersOpen, setFiltersOpen] = useState<boolean>(false);

  // Toast Notifications
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback(
    (title: string, message?: string, type: 'success' | 'info' | 'warning' = 'info') => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, title, message, type }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4000);
    },
    []
  );

  // Fetch Live Data from Fog Services
  const loadFogData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await FogDataService.fetchAllFogData();
      setCapacities(data.capacities);
      setForecasts(data.forecasts);
      setSystemStatus(data.systemStatus);
    } catch (err) {
      console.warn('Could not fetch live multi-fog data; using cached fallback:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadFogData();
    const interval = setInterval(loadFogData, 60000);
    return () => clearInterval(interval);
  }, [loadFogData]);

  // Compute Live Recommendations
  const recommendations: Recommendation[] = useMemo(() => {
    if (allStations.length === 0) return [];
    return rankStations(allStations, driverLocation, forecasts, weights, preferences);
  }, [allStations, driverLocation, forecasts, weights, preferences]);

  const topPick = recommendations[0];

  // Open Technical Details modal
  const handleOpenDetails = (station: Station) => {
    setSelectedStation(station);
    setIsDetailModalOpen(true);
  };

  // Set Destination from any card or modal
  const handleSetDestination = (station: Station) => {
    setActiveDestination(station);
    setSelectedStation(station);
    showToast(
      'Destination Active',
      `Station #${station.id} définie. Itinéraire tracé sur la carte.`,
      'success'
    );
  };

  // Navigate to station (Set + Switch to Map tab)
  const handleNavigateToStation = (station: Station) => {
    setActiveDestination(station);
    setSelectedStation(station);
    setActiveTab('map');
    showToast(
      'Itinéraire Prêt',
      `Station #${station.id} centrée sur la carte.`,
      'success'
    );
  };

  return (
    <div className="min-h-screen comfortable-bg text-slate-900 flex flex-col font-sans relative">

      {/* ── Toast Container ── */}
      <div className="fixed top-[76px] right-4 z-50 flex flex-col gap-2.5 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 px-4 py-3.5 rounded-2xl shadow-lg border animate-slideUp ${
              toast.type === 'success'
                ? 'bg-white border-emerald-200'
                : toast.type === 'warning'
                ? 'bg-white border-amber-200'
                : 'bg-white border-cyan-200'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
            ) : toast.type === 'warning' ? (
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            ) : (
              <Info className="w-5 h-5 text-cyan-500 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              <strong className="block text-sm font-bold text-slate-900">{toast.title}</strong>
              {toast.message && (
                <p className="text-xs text-slate-500 mt-0.5 font-medium leading-snug">{toast.message}</p>
              )}
            </div>
            <button
              onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
              className="text-slate-300 hover:text-slate-600 p-0.5 cursor-pointer transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* ── Header ── */}
      <Header
        systemStatus={systemStatus}
        currentLocation={driverLocation}
        onLocationChange={setDriverLocation}
        onRefresh={loadFogData}
        isRefreshing={isRefreshing}
        onOpenDataProvenance={() => setIsDataProvenanceOpen(true)}
        onToggleFilters={() => setFiltersOpen(!filtersOpen)}
        filtersOpen={filtersOpen}
        activeFogCount={systemStatus.activeFogs.length}
        activeDestination={activeDestination}
        onClearDestination={() => {
          setActiveDestination(null);
          showToast('Destination Annulée', 'La cible active a été retirée.', 'info');
        }}
        onViewDestination={() => {
          if (activeDestination) {
            setSelectedStation(activeDestination);
            setActiveTab('map');
          }
        }}
        onShowToast={showToast}
      />

      {/* ── Tab Bar ── */}
      <div className="bg-white/90 border-b border-slate-200/80 sticky top-[68px] z-30 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-1 py-2" aria-label="Navigation principale">
            {([
              { id: 'recommendations', icon: Sparkles, label: 'Trouver une Borne',   badge: topPick ? 'Top 1' : undefined, activeClass: 'bg-cyan-50 text-cyan-800 border-cyan-300' },
              { id: 'map',             icon: Compass,  label: 'Carte des Bornes',     badge: undefined,                      activeClass: 'bg-emerald-50 text-emerald-800 border-emerald-300' },
              { id: 'forecasts',       icon: Cpu,      label: 'Prévisions IA',        badge: undefined,                      activeClass: 'bg-sky-50 text-sky-800 border-sky-300' },
            ] as const).map(({ id, icon: Icon, label, badge, activeClass }) => {
              const active = activeTab === id;
              return (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as typeof activeTab)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer border ${
                    active ? activeClass : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="hidden sm:inline">{label}</span>
                  {badge && (
                    <span className="ml-0.5 px-2 py-0.5 rounded-full text-[10px] font-black bg-cyan-600 text-white leading-none">
                      {badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* ── Main Content ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-7 sm:py-9 space-y-8">

        {activeTab === 'recommendations' && (
          <div className="space-y-8 animate-fadeIn">
            <RecommendationSection
              recommendations={recommendations}
              weights={weights}
              onWeightsChange={setWeights}
              preferences={preferences}
              onPreferencesChange={setPreferences}
              onOpenDetails={handleOpenDetails}
              onNavigateToStation={handleNavigateToStation}
              selectedStationId={selectedStation?.id || null}
              activeDestinationId={activeDestination?.id || null}
              filtersOpen={filtersOpen}
              onToggleFilters={() => setFiltersOpen(!filtersOpen)}
              onShowToast={showToast}
            />
            <StationMap
              stations={allStations}
              driverLocation={driverLocation}
              selectedStation={selectedStation || topPick?.station || null}
              activeDestination={activeDestination}
              onSelectStation={setSelectedStation}
              onSetDestination={handleSetDestination}
              onOpenDetails={handleOpenDetails}
              territoriesMeta={territoriesMeta}
              recommendedStationId={topPick?.station.id}
            />
          </div>
        )}

        {activeTab === 'map' && (
          <div className="animate-fadeIn">
            <StationMap
              stations={allStations}
              driverLocation={driverLocation}
              selectedStation={selectedStation}
              activeDestination={activeDestination}
              onSelectStation={setSelectedStation}
              onSetDestination={handleSetDestination}
              onOpenDetails={handleOpenDetails}
              territoriesMeta={territoriesMeta}
              recommendedStationId={topPick?.station.id}
            />
          </div>
        )}

        {activeTab === 'forecasts' && (
          <div className="space-y-8 animate-fadeIn">
            <OverviewSection
              capacities={capacities}
              forecasts={forecasts}
              territoriesMeta={territoriesMeta}
              totalStationsCount={allStations.length}
              lastUpdated={systemStatus.lastUpdated}
            />
            <ForecastSection
              forecasts={forecasts}
              capacities={capacities}
              historicalData={historicalOccupancy}
              evaluationData={evaluationData}
              territoriesMeta={territoriesMeta}
            />
          </div>
        )}
      </main>

      {/* ── Modals ── */}
      <StationDetailModal
        isOpen={isDetailModalOpen}
        station={selectedStation}
        onClose={() => setIsDetailModalOpen(false)}
        forecast={selectedStation ? forecasts[selectedStation.fogId] : undefined}
        driverLocation={driverLocation}
        isDestinationActive={activeDestination?.id === selectedStation?.id}
        onSetDestination={handleSetDestination}
        onViewOnMap={(station) => {
          setSelectedStation(station);
          setActiveTab('map');
        }}
      />
      <DataProvenanceModal
        isOpen={isDataProvenanceOpen}
        onClose={() => setIsDataProvenanceOpen(false)}
      />

      <Footer />
    </div>
  );
};
