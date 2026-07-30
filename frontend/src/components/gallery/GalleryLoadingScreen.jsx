import React from 'react';
import { Sparkles } from 'lucide-react';

const GalleryLoadingScreen = ({ loadingProgress, loadingStatus, webGlError }) => {
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-gray-950 text-white overflow-hidden">
      {/* Loading stars/particles background */}
      <div className="absolute inset-0 opacity-30">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white animate-twinkle"
            style={{
              top: `${Math.random() * 100}%`,
              left: `${Math.random() * 100}%`,
              width: `${Math.random() * 3 + 1}px`,
              height: `${Math.random() * 3 + 1}px`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${Math.random() * 5 + 3}s`
            }}
          />
        ))}
      </div>
      
      {/* Loading Content */}
      <div className="z-10 flex flex-col items-center max-w-2xl px-6 text-center">
        <div className="mb-8 relative">
          <div className="absolute -inset-4 rounded-full bg-blue-500/20 blur-xl animate-pulse"></div>
          <Sparkles className="w-16 h-16 text-blue-400 animate-pulse relative z-10" />
        </div>
        
        <h1 className="text-4xl md:text-5xl font-serif text-transparent bg-clip-text bg-gradient-to-r from-blue-200 via-white to-blue-200 mb-6 drop-shadow-sm">
          Entering the Hall of Wisdom
        </h1>
        
        {/* Loading Bar */}
        <div className="w-full max-w-md bg-gray-900 rounded-full h-2 mt-8 mb-4 border border-gray-800 overflow-hidden shadow-inner">
          <div 
            className="bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-500 h-2 rounded-full transition-all duration-300 ease-out relative"
            style={{ width: `${Math.min(loadingProgress, 100)}%` }}
          >
            <div className="absolute top-0 right-0 bottom-0 left-0 bg-white/20 animate-shimmer"></div>
          </div>
        </div>
        
        {/* Loading Status Text */}
        <div className="flex justify-between w-full max-w-md text-sm text-gray-400 font-medium tracking-wide">
          <span className="animate-pulse">{loadingStatus}</span>
          <span>{Math.floor(loadingProgress)}%</span>
        </div>

        {webGlError && (
          <div className="mt-8 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200">
            WebGL is not supported in your browser. The 3D gallery cannot be displayed.
          </div>
        )}
      </div>
    </div>
  );
};

export default GalleryLoadingScreen;
