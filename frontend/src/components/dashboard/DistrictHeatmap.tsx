import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

export const DistrictHeatmap: React.FC = () => {
  const [period, setPeriod] = useState('This Month');
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);

  // Stylized polygonal district paths with intensity levels (1 to 5)
  const districts = [
    { id: 'd1', name: 'Central District', count: 420, color: '#a855f7', path: 'M 140 80 L 175 70 L 190 95 L 170 125 L 135 110 Z' },
    { id: 'd2', name: 'North West', count: 310, color: '#8b5cf6', path: 'M 95 60 L 135 45 L 140 80 L 105 95 L 80 80 Z' },
    { id: 'd3', name: 'North East', count: 240, color: '#6366f1', path: 'M 175 40 L 220 50 L 230 85 L 190 95 L 175 70 Z' },
    { id: 'd4', name: 'East Region', count: 280, color: '#7c3aed', path: 'M 190 95 L 230 85 L 245 120 L 210 145 L 170 125 Z' },
    { id: 'd5', name: 'South East', count: 190, color: '#4f46e5', path: 'M 170 125 L 210 145 L 205 180 L 165 190 L 145 155 Z' },
    { id: 'd6', name: 'South West', count: 220, color: '#4338ca', path: 'M 105 130 L 145 125 L 145 155 L 125 185 L 90 160 Z' },
    { id: 'd7', name: 'West Valley', count: 160, color: '#3730a3', path: 'M 75 90 L 105 95 L 105 130 L 70 135 L 60 110 Z' },
    { id: 'd8', name: 'North Perimeter', count: 110, color: '#312e81', path: 'M 135 45 L 175 40 L 175 70 L 140 80 Z' },
  ];

  return (
    <div className="rounded-2xl bg-[#0d1430] border border-[#1d274d] p-5 shadow-xl flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-white tracking-wide">Inspections by District</h3>
        <button className="flex items-center space-x-1.5 px-2.5 py-1 bg-[#151f42] border border-[#232f58] rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
          <span>{period}</span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>

      {/* Heatmap Graphic & Gradient Scale */}
      <div className="relative flex items-center justify-between flex-1 py-1">
        {/* District SVG Map */}
        <div className="relative w-full h-44 flex items-center justify-center">
          <svg className="w-full h-full" viewBox="40 30 220 170">
            <defs>
              <filter id="mapGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="2" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {districts.map((d) => (
              <path
                key={d.id}
                d={d.path}
                fill={d.color}
                fillOpacity={hoveredDistrict === d.name ? 1 : 0.75}
                stroke="#151b3d"
                strokeWidth="1.5"
                className="transition-all duration-200 cursor-pointer hover:stroke-purple-300 hover:stroke-2"
                onMouseEnter={() => setHoveredDistrict(d.name)}
                onMouseLeave={() => setHoveredDistrict(null)}
              />
            ))}
          </svg>

          {/* Hover Tooltip */}
          {hoveredDistrict && (
            <div className="absolute top-2 left-2 bg-[#1b2349]/90 border border-purple-500/40 rounded-lg px-2.5 py-1 text-[11px] text-white shadow-lg pointer-events-none">
              <div className="font-semibold">{hoveredDistrict}</div>
              <div className="text-purple-300">
                {districts.find(d => d.name === hoveredDistrict)?.count} Inspections
              </div>
            </div>
          )}
        </div>

        {/* Vertical Scale Legend */}
        <div className="flex flex-col items-center justify-between h-36 pl-3 border-l border-[#192348]">
          <span className="text-[10px] text-slate-400 font-medium">High</span>
          {/* Gradient vertical bar */}
          <div className="w-2.5 flex-1 mx-auto my-1.5 rounded-full bg-gradient-to-b from-[#a855f7] via-[#6366f1] to-[#1e1b4b] border border-[#2d3a6d]" />
          <span className="text-[10px] text-slate-400 font-medium">Low</span>
        </div>
      </div>
    </div>
  );
};
