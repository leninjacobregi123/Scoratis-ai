import { useState, useEffect, useRef } from 'react';
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';

export default function LoadingScreen({ onLoadComplete }) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('loading'); // 'loading' | 'complete' | 'zooming' | 'done'
  const assetsRef = useRef({ character: null, socrates: null });

  // Preload 3D assets in background
  useEffect(() => {
    const loadAssets = async () => {
      const fbxLoader = new FBXLoader();
      const gltfLoader = new GLTFLoader();

      try {
        // Stage 1: Initial
        setProgress(10);
        await new Promise(r => setTimeout(r, 300));

        // Stage 2: Load character model
        setProgress(25);
        try {
          const character = await new Promise((resolve, reject) => {
            fbxLoader.load(
              '/models/assassin/assassin_walking.fbx',
              (fbx) => resolve(fbx),
              (prog) => {
                if (prog.total > 0) {
                  setProgress(25 + Math.round((prog.loaded / prog.total) * 25));
                }
              },
              (error) => reject(error)
            );
          });
          assetsRef.current.character = character;
        } catch (e) {
          console.log('Character loading skipped:', e.message);
        }

        // Stage 3: Load Socrates bust
        setProgress(55);
        try {
          const socrates = await new Promise((resolve, reject) => {
            gltfLoader.load(
              '/models/socrates/socrates.glb',
              (gltf) => resolve(gltf),
              (prog) => {
                if (prog.total > 0) {
                  setProgress(55 + Math.round((prog.loaded / prog.total) * 25));
                }
              },
              (error) => reject(error)
            );
          });
          assetsRef.current.socrates = socrates;
        } catch (e) {
          console.log('Socrates loading skipped:', e.message);
        }

        // Stage 4: Complete
        setProgress(90);
        await new Promise(r => setTimeout(r, 300));
        setProgress(100);

        // Show complete state
        await new Promise(r => setTimeout(r, 800));
        setPhase('complete');

        // Start zoom transition
        await new Promise(r => setTimeout(r, 1000));
        setPhase('zooming');

        // Wait for zoom animation to complete
        await new Promise(r => setTimeout(r, 1200));
        setPhase('done');

        onLoadComplete(assetsRef.current);

      } catch (error) {
        console.error('Asset loading error:', error);
        setProgress(100);
        await new Promise(r => setTimeout(r, 500));
        setPhase('complete');
        await new Promise(r => setTimeout(r, 800));
        setPhase('zooming');
        await new Promise(r => setTimeout(r, 1200));
        setPhase('done');
        onLoadComplete(assetsRef.current);
      }
    };

    loadAssets();
  }, [onLoadComplete]);

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden transition-all duration-1000 ease-out ${
        phase === 'done' ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{
        backgroundColor: '#f5f0e6',
        transform: phase === 'zooming' ? 'scale(3)' : 'scale(1)',
        filter: phase === 'zooming' ? 'blur(8px)' : 'blur(0px)',
      }}
    >
      {/* Subtle Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Radial gradient glow */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-30"
          style={{
            background: 'radial-gradient(circle, rgba(107, 124, 94, 0.15) 0%, transparent 70%)'
          }}
        />
        {/* Floating particles */}
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 rounded-full opacity-20 animate-float"
            style={{
              backgroundColor: '#6b7c5e',
              left: `${20 + i * 12}%`,
              top: `${30 + (i % 3) * 20}%`,
              animationDelay: `${i * 0.5}s`,
              animationDuration: `${4 + i}s`
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <div
        className={`text-center max-w-2xl px-8 transition-all duration-700 ${
          phase === 'complete' ? 'opacity-100 transform translate-y-0' :
          phase === 'loading' ? 'opacity-100 transform translate-y-0' : 'opacity-0'
        }`}
      >
        {/* Socrates Bust Image */}
        <div className={`mb-8 transition-all duration-1000 ${
          progress > 50 ? 'opacity-100 transform translate-y-0 scale-100' : 'opacity-0 transform translate-y-4 scale-95'
        }`}>
          <img
            src="/socrates-nobg.png"
            alt="Socrates"
            className="w-32 h-32 mx-auto object-contain"
            style={{
              filter: 'drop-shadow(0 8px 24px rgba(107, 124, 94, 0.3))'
            }}
          />
        </div>

        {/* Academy Name */}
        <p
          className={`text-sm tracking-[0.4em] uppercase mb-6 transition-all duration-700 ${
            progress > 10 ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'
          }`}
          style={{ color: '#6b7c5e', fontWeight: 500 }}
        >
          Scoratis
        </p>

        {/* Decorative Line */}
        <div className={`flex items-center justify-center gap-4 mb-8 transition-all duration-700 delay-100 ${
          progress > 20 ? 'opacity-100' : 'opacity-0'
        }`}>
          <div className="w-12 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
          <div className="w-2 h-2 rotate-45" style={{ backgroundColor: '#b8860b' }} />
          <div className="w-12 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
        </div>

        {/* Main Quote */}
        <h1
          className={`text-3xl md:text-4xl lg:text-5xl font-light leading-tight mb-2 transition-all duration-700 delay-200 ${
            progress > 30 ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'
          }`}
          style={{
            fontFamily: 'Georgia, "Times New Roman", serif',
            color: '#3d4a35',
            letterSpacing: '-0.02em'
          }}
        >
          The unexamined life is
        </h1>
        <h1
          className={`text-3xl md:text-4xl lg:text-5xl italic mb-10 transition-all duration-700 delay-300 ${
            progress > 40 ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'
          }`}
          style={{
            fontFamily: 'Georgia, "Times New Roman", serif',
            color: '#6b7c5e'
          }}
        >
          not worth living.
        </h1>

        {/* Subtitle */}
        <p
          className={`text-base mb-12 transition-all duration-700 delay-400 ${
            progress > 50 ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'
          }`}
          style={{ color: '#8a8a7a', fontFamily: 'Georgia, serif' }}
        >
          {phase === 'complete' ? 'Welcome to your journey of inquiry' : 'Preparing your journey of inquiry...'}
        </p>

        {/* Elegant Loading Bar */}
        <div className={`w-72 mx-auto transition-all duration-500 ${
          phase === 'complete' ? 'opacity-0 transform scale-95' : 'opacity-100'
        }`}>
          <div className="relative">
            {/* Background track */}
            <div
              className="h-[3px] rounded-full overflow-hidden"
              style={{ backgroundColor: 'rgba(107, 124, 94, 0.15)' }}
            >
              {/* Progress fill */}
              <div
                className="h-full transition-all duration-500 ease-out rounded-full relative overflow-hidden"
                style={{
                  width: `${progress}%`,
                  background: 'linear-gradient(90deg, #6b7c5e 0%, #8a9a7a 50%, #b8860b 100%)'
                }}
              >
                {/* Shimmer effect */}
                <div
                  className="absolute inset-0 animate-shimmer"
                  style={{
                    background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)',
                    backgroundSize: '200% 100%'
                  }}
                />
              </div>
            </div>

            {/* Progress percentage */}
            <div className="flex justify-between mt-3">
              <span
                className="text-xs tracking-wider"
                style={{ color: '#a0a090' }}
              >
                {progress < 100 ? 'Loading assets' : 'Ready'}
              </span>
              <span
                className="text-xs font-medium"
                style={{ color: '#6b7c5e' }}
              >
                {progress}%
              </span>
            </div>
          </div>
        </div>

        {/* Enter Button - appears when complete */}
        {phase === 'complete' && (
          <div className="animate-fade-in">
            <div className="flex items-center justify-center gap-2 text-sm" style={{ color: '#6b7c5e' }}>
              <span className="animate-pulse">●</span>
              <span style={{ fontFamily: 'Georgia, serif' }}>Entering...</span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Attribution */}
      <div
        className={`absolute bottom-8 flex items-center gap-3 transition-all duration-700 ${
          progress > 60 ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'
        }`}
      >
        <div className="w-8 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
        <span
          className="text-xs tracking-[0.2em] uppercase"
          style={{ color: '#a0a090', fontFamily: 'Georgia, serif' }}
        >
          Socrates
        </span>
        <div className="w-8 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
      </div>
    </div>
  );
}
