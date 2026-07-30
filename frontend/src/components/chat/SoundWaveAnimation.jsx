import React, { useState, useEffect } from 'react';

export default function SoundWaveAnimation({ isPlaying }) {
  const [heights, setHeights] = useState([12, 16, 10, 18, 14]);

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setHeights(prev => prev.map(() => 8 + Math.random() * 14));
    }, 150);

    return () => clearInterval(interval);
  }, [isPlaying]);

  return (
    <div className="flex items-center gap-0.5">
      {heights.map((h, i) => (
        <div
          key={i}
          className="w-1 bg-gray-700 rounded-full transition-all duration-150"
          style={{ height: `${h}px` }}
        />
      ))}
    </div>
  );
}
