/**
 * ManimAnimationCard Component
 *
 * Displays Manim-generated mathematical animations in chat.
 * Features:
 * - Video player with custom controls
 * - Loading/generating states
 * - Download and fullscreen options
 * - Caption support
 * - Theme-aware styling
 */

import { useState, useRef, useEffect } from 'react';
import {
  Play,
  Pause,
  Maximize2,
  Download,
  RefreshCw,
  Volume2,
  VolumeX,
  Film,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react';

/**
 * Animation status types
 */
const AnimationStatus = {
  QUEUED: 'queued',
  GENERATING: 'generating',
  READY: 'ready',
  ERROR: 'error'
};

/**
 * Format seconds to MM:SS
 */
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Progress bar component
 */
function ProgressBar({ current, duration, onSeek, theme }) {
  const themeClasses = theme?.classes || {};
  const progress = duration > 0 ? (current / duration) * 100 : 0;

  const handleClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    onSeek?.(percent * duration);
  };

  return (
    <div
      onClick={handleClick}
      className="relative h-1.5 bg-gray-200 rounded-full cursor-pointer group"
    >
      <div
        className={`absolute left-0 top-0 h-full rounded-full transition-all
                    ${themeClasses.bgPrimary || 'bg-blue-500'}`}
        style={{ width: `${progress}%` }}
      />
      {/* Hover indicator */}
      <div
        className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full
                   opacity-0 group-hover:opacity-100 transition-opacity
                   bg-white shadow-md border border-gray-200"
        style={{ left: `calc(${progress}% - 6px)` }}
      />
    </div>
  );
}

/**
 * Video player controls
 */
function VideoControls({
  isPlaying,
  isMuted,
  currentTime,
  duration,
  onPlayPause,
  onMuteToggle,
  onSeek,
  onFullscreen,
  onDownload,
  theme
}) {
  const themeClasses = theme?.classes || {};

  return (
    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
      {/* Progress Bar */}
      <ProgressBar
        current={currentTime}
        duration={duration}
        onSeek={onSeek}
        theme={theme}
      />

      {/* Controls Row */}
      <div className="flex items-center justify-between mt-2">
        <div className="flex items-center gap-2">
          {/* Play/Pause */}
          <button
            onClick={onPlayPause}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white"
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>

          {/* Mute Toggle */}
          <button
            onClick={onMuteToggle}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white"
          >
            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>

          {/* Time Display */}
          <span className="text-xs text-white/90 font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Download */}
          <button
            onClick={onDownload}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white"
            title="Download animation"
          >
            <Download size={16} />
          </button>

          {/* Fullscreen */}
          <button
            onClick={onFullscreen}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white"
            title="Fullscreen"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Loading/Generating State Display
 */
function AnimationLoadingState({ status, progress, estimatedTime, theme }) {
  const themeClasses = theme?.classes || {};

  const statusConfig = {
    [AnimationStatus.QUEUED]: {
      icon: Clock,
      text: 'Queued for rendering...',
      color: 'text-amber-500'
    },
    [AnimationStatus.GENERATING]: {
      icon: Loader2,
      text: 'Generating animation...',
      color: themeClasses.textPrimary || 'text-blue-500',
      animate: true
    }
  };

  const config = statusConfig[status];
  if (!config) return null;

  const Icon = config.icon;

  return (
    <div className={`flex flex-col items-center justify-center h-48
                     ${themeClasses.bgSecondary || 'bg-gray-100'} rounded-lg`}>
      <Icon
        size={32}
        className={`${config.color} ${config.animate ? 'animate-spin' : ''}`}
      />
      <p className={`mt-3 font-medium ${themeClasses.text || 'text-gray-700'}`}>
        {config.text}
      </p>

      {/* Progress bar for generation */}
      {status === AnimationStatus.GENERATING && progress !== undefined && (
        <div className="w-48 mt-3">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${themeClasses.bgPrimary || 'bg-blue-500'}`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className={`text-xs mt-1 ${themeClasses.textMuted || 'text-gray-500'}`}>
            {progress}% complete
            {estimatedTime && ` • ~${estimatedTime}s remaining`}
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Error State Display
 */
function AnimationErrorState({ error, onRetry, theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <div className={`flex flex-col items-center justify-center h-48
                     bg-red-50 rounded-lg border border-red-200`}>
      <AlertCircle size={32} className="text-red-500" />
      <p className="mt-3 font-medium text-red-700">Failed to generate animation</p>
      <p className="text-sm text-red-600 mt-1 max-w-xs text-center">
        {error || 'An error occurred during rendering'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                     bg-red-100 text-red-700 hover:bg-red-200 transition-colors
                     text-sm font-medium"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * Main ManimAnimationCard Component
 */
export function ManimAnimationCard({
  videoUrl,
  thumbnailUrl,
  title,
  description,
  code,
  status = AnimationStatus.READY,
  progress,
  estimatedTime,
  error,
  onRetry,
  theme
}) {
  const themeClasses = theme?.classes || {};
  const videoRef = useRef(null);
  const containerRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const [showCode, setShowCode] = useState(false);

  // Update time during playback
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleLoadedMetadata = () => setDuration(video.duration);
    const handleEnded = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('ended', handleEnded);
    };
  }, [videoUrl]);

  // Auto-hide controls after 3 seconds of inactivity
  useEffect(() => {
    if (!isPlaying) return;

    const timeout = setTimeout(() => setShowControls(false), 3000);
    return () => clearTimeout(timeout);
  }, [isPlaying, showControls]);

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleMuteToggle = () => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleSeek = (time) => {
    const video = videoRef.current;
    if (!video) return;

    video.currentTime = time;
    setCurrentTime(time);
  };

  const handleFullscreen = () => {
    const container = containerRef.current;
    if (!container) return;

    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen();
    }
  };

  const handleDownload = () => {
    if (!videoUrl) return;

    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = `${title || 'manim-animation'}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Render loading/generating state
  if (status === AnimationStatus.QUEUED || status === AnimationStatus.GENERATING) {
    return (
      <div className={`rounded-xl overflow-hidden border
                       ${themeClasses.border || 'border-gray-200'}
                       ${themeClasses.bgSecondary || 'bg-white'}`}>
        {/* Header */}
        <div className={`flex items-center gap-2 px-4 py-3 border-b
                         ${themeClasses.border || 'border-gray-200'}
                         ${themeClasses.bgTertiary || 'bg-gray-50'}`}>
          <Film size={18} className={themeClasses.textPrimary || 'text-blue-600'} />
          <span className={`font-medium ${themeClasses.text || 'text-gray-900'}`}>
            {title || 'Mathematical Animation'}
          </span>
        </div>

        {/* Loading State */}
        <div className="p-4">
          <AnimationLoadingState
            status={status}
            progress={progress}
            estimatedTime={estimatedTime}
            theme={theme}
          />
        </div>
      </div>
    );
  }

  // Render error state
  if (status === AnimationStatus.ERROR) {
    return (
      <div className={`rounded-xl overflow-hidden border
                       ${themeClasses.border || 'border-gray-200'}
                       ${themeClasses.bgSecondary || 'bg-white'}`}>
        <div className={`flex items-center gap-2 px-4 py-3 border-b
                         ${themeClasses.border || 'border-gray-200'}
                         ${themeClasses.bgTertiary || 'bg-gray-50'}`}>
          <Film size={18} className="text-red-500" />
          <span className={`font-medium ${themeClasses.text || 'text-gray-900'}`}>
            {title || 'Mathematical Animation'}
          </span>
        </div>
        <div className="p-4">
          <AnimationErrorState error={error} onRetry={onRetry} theme={theme} />
        </div>
      </div>
    );
  }

  // Render video player
  return (
    <div className={`rounded-xl overflow-hidden border
                     ${themeClasses.border || 'border-gray-200'}
                     ${themeClasses.bgSecondary || 'bg-white'}`}>
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-3 border-b
                       ${themeClasses.border || 'border-gray-200'}
                       ${themeClasses.bgTertiary || 'bg-gray-50'}`}>
        <div className="flex items-center gap-2">
          <Film size={18} className={themeClasses.textPrimary || 'text-blue-600'} />
          <span className={`font-medium ${themeClasses.text || 'text-gray-900'}`}>
            {title || 'Mathematical Animation'}
          </span>
          <CheckCircle size={14} className="text-green-500" />
        </div>

        {code && (
          <button
            onClick={() => setShowCode(!showCode)}
            className={`text-xs px-2 py-1 rounded
                        ${themeClasses.bgSecondary || 'bg-gray-100'}
                        ${themeClasses.textMuted || 'text-gray-600'}
                        hover:opacity-80 transition-opacity`}
          >
            {showCode ? 'Hide Code' : 'View Code'}
          </button>
        )}
      </div>

      {/* Video Container */}
      <div
        ref={containerRef}
        className="relative bg-black aspect-video"
        onMouseMove={() => setShowControls(true)}
        onMouseLeave={() => isPlaying && setShowControls(false)}
      >
        <video
          ref={videoRef}
          src={videoUrl}
          poster={thumbnailUrl}
          className="w-full h-full object-contain"
          onClick={handlePlayPause}
          playsInline
        />

        {/* Play button overlay when paused */}
        {!isPlaying && (
          <button
            onClick={handlePlayPause}
            className="absolute inset-0 flex items-center justify-center
                       bg-black/30 hover:bg-black/40 transition-colors"
          >
            <div className={`p-4 rounded-full ${themeClasses.bgPrimary || 'bg-blue-500'}
                           shadow-lg hover:scale-110 transition-transform`}>
              <Play size={32} className="text-white ml-1" />
            </div>
          </button>
        )}

        {/* Controls */}
        {showControls && videoUrl && (
          <VideoControls
            isPlaying={isPlaying}
            isMuted={isMuted}
            currentTime={currentTime}
            duration={duration}
            onPlayPause={handlePlayPause}
            onMuteToggle={handleMuteToggle}
            onSeek={handleSeek}
            onFullscreen={handleFullscreen}
            onDownload={handleDownload}
            theme={theme}
          />
        )}
      </div>

      {/* Description */}
      {description && (
        <div className={`px-4 py-3 border-t ${themeClasses.border || 'border-gray-200'}`}>
          <p className={`text-sm ${themeClasses.text || 'text-gray-700'}`}>
            {description}
          </p>
        </div>
      )}

      {/* Code Panel */}
      {showCode && code && (
        <div className={`border-t ${themeClasses.border || 'border-gray-200'}`}>
          <pre className={`p-4 text-xs font-mono overflow-x-auto
                          ${themeClasses.bgTertiary || 'bg-gray-900'}
                          text-gray-100`}>
            <code>{code}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

export default ManimAnimationCard;
