import React, { useRef, useState } from 'react';
import { Loader2, Play, Pause, Volume2, VolumeX, Film, Download, X } from 'lucide-react';

export default function InlineVideoCard({ video, isGenerating, progress, stage, topic, onRemove }) {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [videoProgress, setVideoProgress] = useState(0);

  const stages = [
    { id: 'content', label: 'Script', icon: '1' },
    { id: 'narration', label: 'Voice', icon: '2' },
    { id: 'rendering', label: 'Render', icon: '3' },
    { id: 'merging', label: 'Done', icon: '4' }
  ];

  const currentIndex = stages.findIndex(s => stage?.includes(s.id));

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const current = videoRef.current.currentTime;
      const duration = videoRef.current.duration;
      setVideoProgress((current / duration) * 100);
    }
  };

  if (isGenerating) {
    return (
      <div className="bg-bg-tertiary border border-border-color rounded-xl p-4 mt-4 animate-fade-in">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gray-200 flex items-center justify-center">
            <Loader2 className="w-5 h-5 text-gray-700 animate-spin" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-text-primary truncate">
              Creating visual explanation...
            </h4>
            <p className="text-xs text-text-muted truncate">{topic}</p>
          </div>
          <span className="text-gray-900 font-bold text-lg">{progress || 0}%</span>
        </div>

        <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-gradient-to-r from-gray-700 to-gray-500 transition-all duration-500 rounded-full"
            style={{ width: `${progress || 0}%` }}
          />
        </div>

        <div className="flex gap-1">
          {stages.map((s, i) => (
            <div
              key={s.id}
              className={`flex-1 py-1.5 rounded text-center text-xs transition-all ${
                i < currentIndex
                  ? 'bg-green-500/20 text-green-400'
                  : i === currentIndex
                  ? 'bg-gray-200 text-gray-700 animate-pulse'
                  : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {i < currentIndex ? '✓' : s.icon}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!video?.path) return null;

  return (
    <div className="bg-bg-tertiary border border-border-color rounded-xl overflow-hidden mt-4 animate-fade-in">
      <div className="relative bg-black aspect-video">
        <video
          ref={videoRef}
          src={video.path}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onEnded={() => setIsPlaying(false)}
          muted={isMuted}
        />

        {!isPlaying && (
          <div
            className="absolute inset-0 flex items-center justify-center bg-black/40 cursor-pointer"
            onClick={togglePlay}
          >
            <div className="w-14 h-14 rounded-full bg-gray-800 flex items-center justify-center hover:bg-gray-900 transition-all hover:scale-110">
              <Play className="w-6 h-6 text-bg-primary ml-1" />
            </div>
          </div>
        )}

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
          <div
            className="h-1 bg-white/30 rounded-full mb-2 cursor-pointer"
            onClick={(e) => {
              if (videoRef.current) {
                const rect = e.currentTarget.getBoundingClientRect();
                const pos = (e.clientX - rect.left) / rect.width;
                videoRef.current.currentTime = pos * videoRef.current.duration;
              }
            }}
          >
            <div
              className="h-full bg-gray-700 rounded-full transition-all"
              style={{ width: `${videoProgress}%` }}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={togglePlay} className="text-white hover:text-gray-300 transition-colors">
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <button onClick={() => setIsMuted(!isMuted)} className="text-white hover:text-gray-300 transition-colors">
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="p-3 flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Film className="w-4 h-4 text-gray-700 flex-shrink-0" />
          <span className="text-sm text-text-primary truncate">{topic}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <a
            href={video.path}
            download={`${topic?.replace(/\s+/g, '_') || 'video'}.mp4`}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all text-xs font-medium"
          >
            <Download className="w-3 h-3" />
            Download
          </a>
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1.5 bg-bg-secondary text-text-muted rounded-lg hover:text-red-400 hover:bg-red-500/10 transition-all"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
