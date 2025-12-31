/**
 * SubjectBackground - Era-Authentic Themed Backgrounds with Particle Effects
 * Renders immersive backgrounds for each subject with unique particle animations
 */

import { useMemo, useEffect } from 'react';
import { getSubjectTheme, getParticleConfig, getBackgroundConfig, isDarkTheme } from '../config/subjectThemes';

/**
 * Particle Generators for each subject type
 */

// Physics - Twinkling Stars
const StarsParticles = ({ config }) => {
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * 3 + 1,
      delay: Math.random() * 5,
      duration: 3 + Math.random() * 4,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full animate-[starTwinkle_3s_ease-in-out_infinite]"
          style={{
            left: `${star.left}%`,
            top: `${star.top}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            backgroundColor: star.color,
            boxShadow: `0 0 ${star.size * 2}px ${star.color}`,
            animationDelay: `${star.delay}s`,
            animationDuration: `${star.duration}s`,
            opacity: config.opacity,
          }}
        />
      ))}
    </div>
  );
};

// Chemistry - Rising Bubbles
const BubblesParticles = ({ config }) => {
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      size: Math.random() * 20 + 8,
      delay: Math.random() * 10,
      duration: 8 + Math.random() * 6,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((bubble) => (
        <div
          key={bubble.id}
          className="absolute rounded-full animate-[bubbleRise_8s_ease-in-out_infinite]"
          style={{
            left: `${bubble.left}%`,
            bottom: '-50px',
            width: `${bubble.size}px`,
            height: `${bubble.size}px`,
            border: `2px solid ${bubble.color}`,
            backgroundColor: `${bubble.color}20`,
            animationDelay: `${bubble.delay}s`,
            animationDuration: `${bubble.duration}s`,
            opacity: config.opacity,
          }}
        />
      ))}
    </div>
  );
};

// Biology - Floating Cells and DNA
const CellsParticles = ({ config }) => {
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * 30 + 15,
      delay: Math.random() * 8,
      duration: 10 + Math.random() * 5,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      type: Math.random() > 0.5 ? 'cell' : 'nucleus',
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((cell) => (
        <div
          key={cell.id}
          className="absolute animate-[cellFloat_10s_ease-in-out_infinite]"
          style={{
            left: `${cell.left}%`,
            top: `${cell.top}%`,
            width: `${cell.size}px`,
            height: `${cell.size}px`,
            borderRadius: cell.type === 'cell' ? '50% 40% 50% 40%' : '50%',
            border: `1.5px solid ${cell.color}`,
            backgroundColor: cell.type === 'nucleus' ? `${cell.color}30` : 'transparent',
            animationDelay: `${cell.delay}s`,
            animationDuration: `${cell.duration}s`,
            opacity: config.opacity,
          }}
        >
          {cell.type === 'cell' && (
            <div
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{
                width: `${cell.size * 0.3}px`,
                height: `${cell.size * 0.3}px`,
                backgroundColor: `${cell.color}50`,
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
};

// Mathematics - Geometric Shapes
const ShapesParticles = ({ config }) => {
  const shapes = ['triangle', 'square', 'circle', 'pentagon'];
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * 25 + 12,
      delay: Math.random() * 8,
      duration: 8 + Math.random() * 4,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      shape: shapes[Math.floor(Math.random() * shapes.length)],
      rotation: Math.random() * 360,
    }));
  }, [config]);

  const getShapeStyle = (shape, size, color) => {
    switch (shape) {
      case 'triangle':
        return {
          width: 0,
          height: 0,
          borderLeft: `${size / 2}px solid transparent`,
          borderRight: `${size / 2}px solid transparent`,
          borderBottom: `${size}px solid ${color}`,
          backgroundColor: 'transparent',
        };
      case 'square':
        return {
          width: `${size}px`,
          height: `${size}px`,
          border: `1.5px solid ${color}`,
        };
      case 'pentagon':
        return {
          width: `${size}px`,
          height: `${size}px`,
          clipPath: 'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
          border: `1.5px solid ${color}`,
          backgroundColor: `${color}20`,
        };
      default: // circle
        return {
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '50%',
          border: `1.5px solid ${color}`,
        };
    }
  };

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((shape) => (
        <div
          key={shape.id}
          className="absolute animate-[shapeRotate_8s_linear_infinite]"
          style={{
            left: `${shape.left}%`,
            top: `${shape.top}%`,
            ...getShapeStyle(shape.shape, shape.size, shape.color),
            animationDelay: `${shape.delay}s`,
            animationDuration: `${shape.duration}s`,
            opacity: config.opacity,
            transform: `rotate(${shape.rotation}deg)`,
          }}
        />
      ))}
    </div>
  );
};

// Computer Science - Binary Rain
const BinaryParticles = ({ config }) => {
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 10,
      duration: 6 + Math.random() * 6,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      chars: Array.from({ length: 8 }, () => Math.random() > 0.5 ? '1' : '0').join(''),
      fontSize: Math.random() * 8 + 10,
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((binary) => (
        <div
          key={binary.id}
          className="absolute animate-[binaryFall_8s_linear_infinite] font-mono"
          style={{
            left: `${binary.left}%`,
            top: '-100px',
            color: binary.color,
            fontSize: `${binary.fontSize}px`,
            animationDelay: `${binary.delay}s`,
            animationDuration: `${binary.duration}s`,
            opacity: config.opacity,
            writingMode: 'vertical-rl',
            textOrientation: 'upright',
            letterSpacing: '3px',
            textShadow: `0 0 10px ${binary.color}`,
          }}
        >
          {binary.chars}
        </div>
      ))}
    </div>
  );
};

// English - Floating Quills and Letters
const QuillsParticles = ({ config }) => {
  const symbols = ['✒', '✎', '❧', '☙', 'A', 'B', 'C', '&', '§'];
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      delay: Math.random() * 6,
      duration: 6 + Math.random() * 4,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      symbol: symbols[Math.floor(Math.random() * symbols.length)],
      fontSize: Math.random() * 16 + 14,
      rotation: Math.random() * 40 - 20,
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((quill) => (
        <div
          key={quill.id}
          className="absolute animate-[quillFloat_6s_ease-in-out_infinite]"
          style={{
            left: `${quill.left}%`,
            top: `${quill.top}%`,
            color: quill.color,
            fontSize: `${quill.fontSize}px`,
            animationDelay: `${quill.delay}s`,
            animationDuration: `${quill.duration}s`,
            opacity: config.opacity,
            transform: `rotate(${quill.rotation}deg)`,
            fontFamily: 'Georgia, serif',
          }}
        >
          {quill.symbol}
        </div>
      ))}
    </div>
  );
};

// History - Dust and Ancient Symbols
const DustParticles = ({ config }) => {
  const symbols = ['Ω', 'Δ', 'Σ', 'Φ', 'Ψ', '☥', '⚱', '⚔', '•'];
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      delay: Math.random() * 20,
      duration: 15 + Math.random() * 10,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      type: Math.random() > 0.6 ? 'symbol' : 'dust',
      symbol: symbols[Math.floor(Math.random() * symbols.length)],
      size: Math.random() * 4 + 2,
      fontSize: Math.random() * 14 + 12,
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((particle) => (
        <div
          key={particle.id}
          className="absolute animate-[dustDrift_20s_linear_infinite]"
          style={{
            left: `${particle.left}%`,
            top: `${particle.top}%`,
            animationDelay: `${particle.delay}s`,
            animationDuration: `${particle.duration}s`,
            opacity: config.opacity,
            ...(particle.type === 'dust'
              ? {
                  width: `${particle.size}px`,
                  height: `${particle.size}px`,
                  borderRadius: '50%',
                  backgroundColor: particle.color,
                }
              : {
                  color: particle.color,
                  fontSize: `${particle.fontSize}px`,
                  fontFamily: 'Georgia, serif',
                }),
          }}
        >
          {particle.type === 'symbol' && particle.symbol}
        </div>
      ))}
    </div>
  );
};

// Philosophy - Light Rays
const RaysParticles = ({ config }) => {
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: 10 + (i * (80 / config.count)),
      delay: Math.random() * 5,
      duration: 5 + Math.random() * 3,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      width: Math.random() * 3 + 1,
      height: Math.random() * 300 + 200,
      angle: Math.random() * 20 - 10,
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((ray) => (
        <div
          key={ray.id}
          className="absolute animate-[rayPulse_5s_ease-in-out_infinite]"
          style={{
            left: `${ray.left}%`,
            top: 0,
            width: `${ray.width}px`,
            height: `${ray.height}px`,
            background: `linear-gradient(180deg, ${ray.color}40 0%, ${ray.color}10 50%, transparent 100%)`,
            animationDelay: `${ray.delay}s`,
            animationDuration: `${ray.duration}s`,
            opacity: config.opacity,
            transform: `rotate(${ray.angle}deg)`,
            transformOrigin: 'top center',
          }}
        />
      ))}
    </div>
  );
};

// Psychology - Neural Connections
const NeuronsParticles = ({ config }) => {
  const particles = useMemo(() => {
    const nodes = Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      delay: Math.random() * 4,
      duration: 4 + Math.random() * 3,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      size: Math.random() * 8 + 4,
    }));
    return nodes;
  }, [config]);

  // Generate connections between nearby nodes
  const connections = useMemo(() => {
    const conns = [];
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].left - particles[j].left;
        const dy = particles[i].top - particles[j].top;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 25 && conns.length < 30) {
          conns.push({
            id: `${i}-${j}`,
            x1: particles[i].left,
            y1: particles[i].top,
            x2: particles[j].left,
            y2: particles[j].top,
            color: particles[i].color,
          });
        }
      }
    }
    return conns;
  }, [particles]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Connection lines */}
      <svg className="absolute inset-0 w-full h-full" style={{ opacity: config.opacity * 0.5 }}>
        {connections.map((conn) => (
          <line
            key={conn.id}
            x1={`${conn.x1}%`}
            y1={`${conn.y1}%`}
            x2={`${conn.x2}%`}
            y2={`${conn.y2}%`}
            stroke={conn.color}
            strokeWidth="1"
            className="animate-[neuronPulse_4s_ease-in-out_infinite]"
          />
        ))}
      </svg>
      {/* Nodes */}
      {particles.map((node) => (
        <div
          key={node.id}
          className="absolute rounded-full animate-[neuronPulse_4s_ease-in-out_infinite]"
          style={{
            left: `${node.left}%`,
            top: `${node.top}%`,
            width: `${node.size}px`,
            height: `${node.size}px`,
            backgroundColor: node.color,
            boxShadow: `0 0 ${node.size}px ${node.color}`,
            animationDelay: `${node.delay}s`,
            animationDuration: `${node.duration}s`,
            opacity: config.opacity,
          }}
        />
      ))}
    </div>
  );
};

// Economics - Coins and Mini Graphs
const CoinsParticles = ({ config }) => {
  const particles = useMemo(() => {
    return Array.from({ length: config.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      delay: Math.random() * 4,
      duration: 3 + Math.random() * 2,
      spinDuration: 4 + Math.random() * 3,
      color: config.colors[Math.floor(Math.random() * config.colors.length)],
      size: Math.random() * 20 + 15,
      type: Math.random() > 0.7 ? 'graph' : 'coin',
    }));
  }, [config]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((particle) => (
        <div
          key={particle.id}
          className={`absolute ${particle.type === 'coin' ? 'animate-[coinFloat_3s_ease-in-out_infinite]' : ''}`}
          style={{
            left: `${particle.left}%`,
            top: `${particle.top}%`,
            animationDelay: `${particle.delay}s`,
            animationDuration: `${particle.duration}s`,
            opacity: config.opacity,
          }}
        >
          {particle.type === 'coin' ? (
            <div
              className="rounded-full border-2 flex items-center justify-center font-bold animate-[coinSpin_4s_linear_infinite]"
              style={{
                width: `${particle.size}px`,
                height: `${particle.size}px`,
                borderColor: particle.color,
                color: particle.color,
                fontSize: `${particle.size * 0.5}px`,
                animationDuration: `${particle.spinDuration}s`,
              }}
            >
              $
            </div>
          ) : (
            <svg
              width={particle.size}
              height={particle.size * 0.6}
              viewBox="0 0 40 24"
              fill="none"
              style={{ opacity: 0.7 }}
            >
              <polyline
                points="0,20 10,15 20,18 30,8 40,12"
                stroke={particle.color}
                strokeWidth="2"
                fill="none"
              />
              <circle cx="40" cy="12" r="3" fill={particle.color} />
            </svg>
          )}
        </div>
      ))}
    </div>
  );
};

/**
 * Particle Renderer - Selects the appropriate particle component
 */
const ParticleRenderer = ({ type, config }) => {
  const particleComponents = {
    stars: StarsParticles,
    bubbles: BubblesParticles,
    cells: CellsParticles,
    shapes: ShapesParticles,
    binary: BinaryParticles,
    quills: QuillsParticles,
    dust: DustParticles,
    rays: RaysParticles,
    neurons: NeuronsParticles,
    coins: CoinsParticles,
  };

  const ParticleComponent = particleComponents[type];
  if (!ParticleComponent) return null;

  return <ParticleComponent config={config} />;
};

/**
 * SubjectBackground Component
 * Renders an immersive era-authentic background with particles
 */
export default function SubjectBackground({ subjectId, children }) {
  // Get theme configuration
  const theme = useMemo(() => getSubjectTheme(subjectId), [subjectId]);
  const particleConfig = useMemo(() => getParticleConfig(subjectId), [subjectId]);
  const backgroundConfig = useMemo(() => getBackgroundConfig(subjectId), [subjectId]);
  const isDark = useMemo(() => isDarkTheme(subjectId), [subjectId]);

  // Inject CSS custom properties for dynamic theming
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--theme-primary', theme.colors.primary);
    root.style.setProperty('--theme-accent', theme.colors.accent);
    root.style.setProperty('--theme-bg-primary', theme.colors.bgPrimary);
    root.style.setProperty('--theme-bg-secondary', theme.colors.bgSecondary);
    root.style.setProperty('--theme-text-primary', theme.colors.textPrimary);
    root.style.setProperty('--theme-text-secondary', theme.colors.textSecondary);
    root.style.setProperty('--theme-border', theme.colors.border);

    // Add theme class to body for scrollbar styling
    document.body.className = document.body.className
      .replace(/theme-\w+/g, '')
      .trim();
    document.body.classList.add(`theme-${subjectId || 'philosophy'}`);

    return () => {
      // Cleanup on unmount
      document.body.classList.remove(`theme-${subjectId || 'philosophy'}`);
    };
  }, [theme, subjectId]);

  return (
    <div
      className={`relative h-full w-full transition-all duration-700 ease-in-out ${theme.classes.pageBg}`}
      style={{
        background: backgroundConfig?.gradient || undefined,
      }}
    >
      {/* Background gradient overlay for depth */}
      <div
        className="fixed inset-0 pointer-events-none transition-opacity duration-700"
        style={{
          background: backgroundConfig?.gradient,
          opacity: 0.9,
        }}
      />

      {/* Subtle texture overlay - lighter for light themes, darker for dark */}
      <div
        className={`fixed inset-0 pointer-events-none transition-opacity duration-700 ${
          isDark ? 'opacity-[0.03]' : 'opacity-[0.015]'
        }`}
        style={{
          backgroundImage: isDark
            ? 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 400 400\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")'
            : 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 400 400\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.65\' numOctaves=\'3\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")',
        }}
      />

      {/* Particle effects layer */}
      {particleConfig && (
        <div className="fixed inset-0 pointer-events-none z-0 transition-opacity duration-700">
          <ParticleRenderer type={particleConfig.type} config={particleConfig} />
        </div>
      )}

      {/* Vignette effect for immersion (dark themes only) */}
      {isDark && (
        <div
          className="fixed inset-0 pointer-events-none transition-opacity duration-700"
          style={{
            background: 'radial-gradient(ellipse at center, transparent 0%, rgba(0,0,0,0.3) 100%)',
          }}
        />
      )}

      {/* Content layer - full height for flex layouts */}
      <div className="relative z-10 h-full w-full flex flex-col">
        {children}
      </div>
    </div>
  );
}
