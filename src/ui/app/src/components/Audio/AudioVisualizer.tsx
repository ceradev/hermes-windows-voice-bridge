import React from 'react';

interface AudioVisualizerProps {
  audioLevel: number; // 0.0 to 1.0
  isActive: boolean;  
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ audioLevel, isActive }) => {
  const normalizedLevel = Math.min(1, Math.max(0, audioLevel));
  const wavePoints = Array.from({ length: 40 }, (_, i) => {
    const x = i * 4.4;
    const y = isActive
      ? 40 + Math.sin(i * 0.5 + normalizedLevel * 10) * (normalizedLevel * 30 + 5)
      : 40;
    return `${x},${y}`;
  }).join(' ');
  
  return (
    <div className="flex w-full max-w-[176px] flex-col gap-2 font-mono">
      <div className="relative h-20 w-44 overflow-hidden rounded-[6px] border border-black/20 bg-black text-white dark:border-white/20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] bg-[size:16px_16px] opacity-20" />
        <div className="absolute left-0 right-0 top-1/2 h-px bg-white/20" />
        <svg viewBox="0 0 176 80" className="relative z-10 h-full w-full">
          <polyline
            points={wavePoints}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="square"
          />
        </svg>
      </div>
      <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500 dark:text-gray-400">
        <span>{isActive ? 'Signal' : 'Standby'}</span>
        <span>{Math.round(normalizedLevel * 100).toString().padStart(3, '0')}%</span>
      </div>
    </div>
  );
};
