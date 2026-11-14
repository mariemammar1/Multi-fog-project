import React from 'react';
import { Zap } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white py-10 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 pb-6 border-b border-slate-100">
          {/* Col 1 */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-slate-900 font-bold text-sm">
              <Zap className="w-4 h-4 text-cyan-600" />
              <span>Multi-Fog EV Network</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Collaborative Multi-Fog Architecture and DevOps for Intelligent Optimization of an Electric Vehicle Charging Network.
            </p>
          </div>

          {/* Col 2 */}
          <div className="space-y-2">
            <span className="font-bold text-slate-800 block uppercase tracking-wider text-[11px]">
              Topologie Multi-Fog
            </span>
            <ul className="space-y-1 text-[11px] text-slate-600">
              <li>• <strong>Fog A :</strong> Port 8001 (Centre - Nanshan / Futian)</li>
              <li>• <strong>Fog B :</strong> Port 8002 (Est - Luohu / Longgang)</li>
              <li>• <strong>Fog C :</strong> Port 8003 (Ouest - Bao'an / Qianhai)</li>
              <li>• <strong>Chronos-2 ML :</strong> Port 8000 (Inférence séries temporelles)</li>
            </ul>
          </div>

          {/* Col 3 */}
          <div className="space-y-2">
            <span className="font-bold text-slate-800 block uppercase tracking-wider text-[11px]">
              Recherche & Modèles
            </span>
            <ul className="space-y-1 text-[11px] text-slate-600">
              <li>• <strong>Amazon Chronos-2 :</strong> Pipeline probabiliste zero-shot</li>
              <li>• <strong>Dataset :</strong> UrbanEV (1 635 stations, 22 138 bornes)</li>
              <li>• <strong>Horizon :</strong> +1 heure d'avance sur l'occupation globale</li>
              <li>• <strong>Évaluation :</strong> MAE benchmarkée face à la persistance</li>
            </ul>
          </div>

          {/* Col 4 */}
          <div className="space-y-2">
            <span className="font-bold text-slate-800 block uppercase tracking-wider text-[11px]">
              Garanties DevOps
            </span>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Consommateur frontend en lecture seule. Les flux de négociation HELP_REQUEST, les verrous temporaires et les contraintes de base SQLite restent intacts.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-500">
          <div>
            &copy; 2026 Architecture Collaborative Multi-Fog EV. Tous droits réservés.
          </div>
          <div className="flex items-center space-x-4">
            <span className="flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5" />
              Microservices FastAPI + Chronos-2
            </span>
            <span>•</span>
            <span className="flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 mr-1.5" />
              React + TypeScript + Tailwind
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
