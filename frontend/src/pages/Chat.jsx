import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  ArrowUp, MessageSquare, Plus,
  MoreVertical, Trash2, Edit2, Check, X,
  Play, Loader2, Download, Film, Pause, Volume2, VolumeX, Mic, MicOff, FileText,
  Globe, Brain, Share2, Link2, Copy, AlertTriangle
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import SocratesLogo from '../3d/SocratesLogo';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import LLMSwitcher from '../components/LLMSwitcher';
import { THEME, TUTOR, getStandardizedThemeClasses } from '../config/subjectThemes';
import { parseCitations, buildSourceMap, hasCitations } from '../utils/citations';
import { getAuthHeaders, refreshAccessToken, clearTokens } from '../utils/auth';
import { CitationNumber, CitationPopup, CitationList, SourcesBadge, FootnotesSection } from '../components/Citation';
import AgenticWorkflow, { useAgenticWorkflow } from '../components/AgenticWorkflow';
import { AttachmentButton, AttachmentPreview, UploadProgressOverlay } from '../components/ChatAttachments';
import { ChatOptionsBar, DEFAULT_CHAT_OPTIONS } from '../components/ChatOptions';
import { CanvasPanel, CanvasToggleButton } from '../components/CanvasPanel';
import { SearchTrailIndicator, SearchFallbackIndicator } from '../components/SearchTrailIndicator';
import WebSearchProgress, { WebSearchProgressLight } from '../components/WebSearchProgress';
import ClarificationRequest from '../components/ClarificationRequest';
import ManimAnimationCard from '../components/ManimAnimationCard';
import { LinkPreviewCard, LinkPreviewGrid } from '../components/LinkPreviewCard';
import { InlineImage, ImageGallery } from '../components/InlineImage';

// Streaming chat endpoints use raw fetch() (SSE needs a readable stream,
// which axios doesn't expose the same way), so they don't get the silent
// 401-refresh-and-retry that useApi.js's axios interceptor gives every other
// request in the app. Without this, an expired access token (30min default)
// mid-conversation surfaced as an opaque "I apologize, but I encountered an
// error" - indistinguishable from a real AI/backend failure - instead of
// transparently refreshing or sending the user to log back in.
async function fetchWithAuthRetry(url, options) {
  const response = await fetch(url, options);
  if (response.status !== 401) return response;

  const newToken = await refreshAccessToken();
  if (!newToken) {
    clearTokens();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    return response;
  }

  return fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${newToken}` },
  });
}

// ============== UI COMPONENTS ==============

// Sound wave animation for voice playback
function SoundWaveAnimation({ isPlaying }) {
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

// Inline Video Card - Shows video progress or player directly in message flow
function InlineVideoCard({ video, isGenerating, progress, stage, topic, error, onRemove }) {
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
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
      return;
    }
    // play() returns a promise that can reject (autoplay policy, decode
    // failure, etc.) - previously isPlaying was set to true unconditionally
    // right after calling play(), regardless of whether it actually
    // succeeded. That hid the overlay (shown only when !isPlaying) even
    // when playback silently failed, so clicking play looked like it did
    // something but no video ever appeared, with no way to click play again.
    videoRef.current.play()
      .then(() => setIsPlaying(true))
      .catch((err) => {
        console.error('Video playback failed:', err);
        setIsPlaying(false);
      });
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const current = videoRef.current.currentTime;
      const duration = videoRef.current.duration;
      setVideoProgress((current / duration) * 100);
    }
  };

  // Failed / timed-out generation - the only branch that previously didn't
  // exist, so a failed job just silently vanished with no explanation.
  if (error) {
    return (
      <div className="bg-red-500/5 border border-red-300/50 rounded-xl p-4 mt-4 animate-fade-in">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-500" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-text-primary">Video generation failed</h4>
            <p className="text-xs text-text-muted mt-0.5 truncate" title={topic}>{topic}</p>
            <p className="text-xs text-red-500/80 mt-1 line-clamp-2">{error}</p>
          </div>
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1.5 text-text-muted rounded-lg hover:text-red-400 hover:bg-red-500/10 transition-all flex-shrink-0"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Generation progress state
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

        {/* Progress bar */}
        <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-gradient-to-r from-gray-700 to-gray-500 transition-all duration-500 rounded-full"
            style={{ width: `${progress || 0}%` }}
          />
        </div>

        {/* Stage indicators */}
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

  // Completed video player
  if (!video?.path) return null;

  return (
    <div className="bg-bg-tertiary border border-border-color rounded-xl overflow-hidden mt-4 animate-fade-in">
      {/* Video container */}
      <div className="relative bg-black aspect-video">
        <video
          ref={videoRef}
          src={video.path}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onEnded={() => setIsPlaying(false)}
          muted={isMuted}
        />

        {/* Play overlay */}
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

        {/* Video controls overlay */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
          {/* Progress bar */}
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

      {/* Video info */}
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

// Video Offer Card - Shows when video_available is true
// NEW: Simplified design for user-triggered video generation
function VideoOfferCard({ recommendation, onAccept, onDismiss }) {
  if (!recommendation || !recommendation.available) return null;

  const { topic, concepts = [], type } = recommendation;

  // Get visualization type label
  const typeLabels = {
    process: 'Process',
    structure: 'Structure',
    concept: 'Concept',
    comparison: 'Comparison',
    transformation: 'Transformation'
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mt-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
          <Film className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-blue-900">Visual Explanation Available</h4>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              15-30s
            </span>
          </div>

          {/* Topic */}
          {topic && (
            <p className="text-sm text-blue-800 font-medium mb-2">{topic}</p>
          )}

          {/* Visualization type */}
          {type && typeLabels[type] && (
            <span className="inline-block text-xs bg-white/70 text-blue-700 px-2 py-0.5 rounded mb-2">
              {typeLabels[type]}
            </span>
          )}

          {/* Key concepts */}
          {concepts.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {concepts.slice(0, 3).map((concept, i) => (
                <span key={i} className="text-xs px-2 py-0.5 bg-white rounded-full text-gray-700 border border-gray-200">
                  {concept}
                </span>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={onAccept}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 shadow-sm"
            >
              <Play className="w-4 h-4" />
              Generate Video
            </button>
            <button
              onClick={onDismiss}
              className="px-4 py-2 bg-white text-gray-600 text-sm rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
            >
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper function to strip pedagogical plan from AI responses
function stripPedagogicalPlan(content) {
  if (!content) return content;
  // Remove <pedagogical_plan>...</pedagogical_plan> sections (including multi-line)
  return content
    .replace(/<pedagogical_plan>[\s\S]*?<\/pedagogical_plan>/gi, '')
    .replace(/\*\*<pedagogical_plan>\*\*[\s\S]*?<\/pedagogical_plan>/gi, '')
    .trim();
}

// Message card - Claude.ai inspired professional design
function MessageCard({
  message,
  index,
  audioUrl,
  isCurrentlyPlaying,
  isLoadingAudio,
  onPlayAudio,
  onPauseAudio,
  video,
  generatingVideo,
  onRemoveVideo,
  videoRecommendation,
  onAcceptVideo,
  onDismissVideo,
  theme,
  sources,
  workflow,
  onCitationClick,
  // New props for enhanced features
  searchTrail,
  clarification,
  animations,
  linkPreviews,
  images,
  onSuggestionClick
}) {
  const isUser = message.role === 'user';
  const [isVisible, setIsVisible] = useState(false);
  const [showVideoOffer, setShowVideoOffer] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const [showSourcesList, setShowSourcesList] = useState(false);

  // Get theme classes (use defaults if no theme provided)
  const t = theme || THEME;

  // Get avatar image for AI responses (use tutor portrait)
  const avatarImage = TUTOR.portrait;

  // Process content to hide pedagogical plan for AI messages
  const strippedContent = isUser ? message.content : stripPedagogicalPlan(message.content);

  // Build source map for citations
  const sourceMap = useMemo(() => buildSourceMap(sources), [sources]);

  // Parse citations from message content
  const { cleanContent, citations } = useMemo(() => {
    if (isUser || !strippedContent) {
      return { cleanContent: strippedContent, citations: [] };
    }
    return parseCitations(strippedContent);
  }, [strippedContent, isUser]);

  // Use cleanContent if we have citations, otherwise use stripped content
  const displayContent = citations.length > 0 ? cleanContent : strippedContent;

  // Handle citation click
  const handleCitationClick = useCallback((chunkId) => {
    const source = sourceMap.get(chunkId);
    if (source) {
      setActiveCitation(activeCitation?.chunkId === chunkId ? null : source);
    }
  }, [sourceMap, activeCitation]);

  // Update showVideoOffer when videoRecommendation changes (arrives from streaming)
  useEffect(() => {
    if (videoRecommendation && !video && !generatingVideo) {
      setShowVideoOffer(true);
    }
  }, [videoRecommendation, video, generatingVideo]);

  // Handle video offer acceptance
  const handleAcceptVideo = () => {
    setShowVideoOffer(false);
    if (onAcceptVideo) onAcceptVideo(videoRecommendation, message.id);
  };

  // Handle video offer dismissal
  const handleDismissVideo = () => {
    setShowVideoOffer(false);
    if (onDismissVideo) onDismissVideo(message.id);
  };

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), index * 50);
    return () => clearTimeout(timer);
  }, [index]);

  return (
    <div
      className={`transform transition-all duration-500 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'} ${
        isUser ? '' : `${t.classes.aiMsgBg} backdrop-blur-sm -mx-4 px-4 sm:-mx-6 sm:px-6`
      } py-6`}
    >
      <div className="max-w-3xl mx-auto">
        {/* Label with tutor avatar and timestamp */}
        <div className={`flex items-center gap-3 mb-4 ${isUser ? 'justify-end' : ''}`}>
          {!isUser && avatarImage && (
            <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-gray-300 shadow-md flex-shrink-0">
              <img
                src={avatarImage}
                alt={TUTOR.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  if (e.target.src.endsWith('/socrates-nobg.png')) { e.target.style.display = 'none'; return; }
                  e.target.src = '/socrates-nobg.png';
                }}
              />
            </div>
          )}
          <div className={`flex flex-col ${isUser ? 'items-end' : ''}`}>
            <span className={`text-sm font-medium ${isUser ? 'text-text-muted' : t.classes.aiMsgAccent}`}>
              {isUser ? 'You' : TUTOR.name}
            </span>
            {!isUser && (
              <span className="text-xs text-text-muted/70">{TUTOR.title}</span>
            )}
          </div>
          <span className="text-xs text-text-muted/60">·</span>
          <span className="text-xs text-text-muted/60">{message.timestamp}</span>
        </div>

        {/* Content */}
        {isUser ? (
          <div className="ml-auto max-w-[85%]">
            <div className={`${t.classes.userMsgBg} rounded-2xl rounded-tr-sm px-5 py-4 border ${t.classes.userMsgBorder} backdrop-blur-sm`}>
              <p className={`text-base leading-7 ${t.classes.userMsgText}`}>{message.content}</p>
            </div>
          </div>
        ) : (
          <div>
            {/* Clarification Request - when agent needs user help */}
            {clarification && (
              <ClarificationRequest
                reason={clarification.reason}
                suggestions={clarification.suggestions}
                searchTrail={clarification.searchTrail}
                onSuggestionClick={onSuggestionClick}
                theme={theme}
              />
            )}

            {/* Manim Animations */}
            {animations && animations.length > 0 && (
              <div className="space-y-3 mt-4">
                {animations.map((anim, idx) => (
                  <ManimAnimationCard
                    key={idx}
                    videoUrl={anim.videoUrl}
                    thumbnailUrl={anim.thumbnailUrl}
                    title={anim.title}
                    description={anim.description}
                    code={anim.code}
                    status={anim.status}
                    theme={theme}
                  />
                ))}
              </div>
            )}

            {/* Link Previews */}
            {linkPreviews && linkPreviews.length > 0 && (
              <div className="mt-4">
                <LinkPreviewGrid links={linkPreviews} theme={theme} />
              </div>
            )}

            {/* Inline Images */}
            {images && images.length > 0 && (
              <div className="mt-4">
                <ImageGallery images={images} theme={theme} />
              </div>
            )}

            <div className="prose prose-lg max-w-none">
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <div className="relative my-4 rounded-xl overflow-hidden border border-border-color">
                        <div className="flex items-center justify-between px-4 py-2 bg-bg-tertiary border-b border-border-color">
                          <span className="text-xs text-gray-600 font-mono">{match[1]}</span>
                        </div>
                        <SyntaxHighlighter
                          style={oneLight}
                          language={match[1]}
                          PreTag="div"
                          className="!bg-bg-tertiary !m-0 !rounded-none !text-sm"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      </div>
                    ) : (
                      <code className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-800 font-mono text-sm" {...props}>
                        {children}
                      </code>
                    );
                  },
                  p: ({ children }) => <p className="text-base leading-7 text-text-primary mb-5 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="space-y-3 mb-5 last:mb-0">{children}</ul>,
                  ol: ({ children }) => <ol className="space-y-3 mb-5 last:mb-0 list-decimal list-inside">{children}</ol>,
                  li: ({ children }) => (
                    <li className="flex items-start gap-3 text-base leading-7">
                      <span className="text-gray-500 mt-2.5 text-[8px]">●</span>
                      <span className="text-text-primary">{children}</span>
                    </li>
                  ),
                  h1: ({ children }) => <h1 className="text-2xl font-light text-text-primary mb-4 mt-6 first:mt-0" style={{ fontFamily: 'Georgia, serif' }}>{children}</h1>,
                  h2: ({ children }) => <h2 className="text-xl font-light text-text-primary mb-3 mt-5 first:mt-0" style={{ fontFamily: 'Georgia, serif' }}>{children}</h2>,
                  h3: ({ children }) => <h3 className="text-lg font-medium text-text-primary mb-3 mt-4 first:mt-0">{children}</h3>,
                  blockquote: ({ children }) => (
                    <blockquote className="pl-5 my-5 text-text-muted italic border-l-2 border-gray-300 text-base leading-7">
                      {children}
                    </blockquote>
                  ),
                  strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
                  em: ({ children }) => <em className="text-gray-700 font-medium not-italic">{children}</em>,
                }}
              >
                {displayContent}
              </ReactMarkdown>
            </div>

            {/* Voice controls for AI messages */}
            {(audioUrl || isLoadingAudio) && (
              <div className="flex items-center gap-3 mt-6 pt-4 border-t border-border-color/30">
                {isLoadingAudio ? (
                  <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-bg-tertiary text-text-muted text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Preparing voice...
                  </div>
                ) : (
                  <button
                    onClick={() => isCurrentlyPlaying ? onPauseAudio() : onPlayAudio(audioUrl, message.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all text-sm font-medium ${
                      isCurrentlyPlaying
                        ? 'bg-gray-800 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {isCurrentlyPlaying ? (
                      <>
                        <Pause className="w-4 h-4" />
                        Pause
                      </>
                    ) : (
                      <>
                        <Volume2 className="w-4 h-4" />
                        Listen to {TUTOR.name}
                      </>
                    )}
                  </button>
                )}
                {isCurrentlyPlaying && (
                  <div className="flex items-center gap-2">
                    <SoundWaveAnimation isPlaying={true} />
                    <span className="text-sm text-text-muted">Speaking...</span>
                  </div>
                )}
              </div>
            )}

            {/* Inline video section - shows after AI messages */}
            {(video || generatingVideo) && (
              <InlineVideoCard
                video={video}
                isGenerating={!!generatingVideo && !generatingVideo.error}
                progress={generatingVideo?.progress}
                stage={generatingVideo?.stage}
                topic={generatingVideo?.topic || video?.topic}
                error={generatingVideo?.error}
                onRemove={onRemoveVideo}
              />
            )}

            {/* Contextual video offer - based on learning state */}
            {showVideoOffer && videoRecommendation && !video && !generatingVideo && (
              <VideoOfferCard
                recommendation={videoRecommendation}
                onAccept={handleAcceptVideo}
                onDismiss={handleDismissVideo}
              />
            )}

            {/* Sources section for citations */}
            {sources && sources.length > 0 && (
              <div className="mt-6 pt-4 border-t border-border-color/30">
                <button
                  onClick={() => setShowSourcesList(!showSourcesList)}
                  className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  <span>{sources.length} source{sources.length !== 1 ? 's' : ''} referenced</span>
                  <span className="text-xs">{showSourcesList ? '(hide)' : '(show)'}</span>
                </button>

                {showSourcesList && (
                  <div className="mt-3 space-y-2">
                    {sources.map((source, i) => (
                      <button
                        key={source.chunk_id || i}
                        onClick={() => onCitationClick?.(source)}
                        className="w-full flex items-start gap-3 p-3 rounded-lg bg-bg-tertiary/50 border border-border-color/30 hover:bg-bg-tertiary hover:border-blue-300 transition-colors text-left cursor-pointer"
                      >
                        <span className="flex items-center justify-center w-6 h-6 bg-blue-100 text-blue-700 rounded text-xs font-bold flex-shrink-0">
                          {source.citation_number || i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {source.document_title || 'Unknown Document'}
                          </p>
                          <p className="text-xs text-text-muted mt-0.5 line-clamp-2">
                            {source.content_preview || source.content?.substring(0, 150)}...
                          </p>
                          {source.page && (
                            <p className="text-xs text-text-muted/60 mt-1">Page {source.page}</p>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Typing indicator - Theme-aware
function TypingIndicator({ theme, isDark }) {
  const displayName = 'Socrates';

  return (
    <div className={`py-6 animate-fade-in ${isDark ? 'bg-white/5' : 'bg-bg-secondary/50'}`}>
      <div className="max-w-3xl mx-auto px-6">
        <div className="flex items-center gap-2 mb-4">
          <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-800'}`}>{displayName}</span>
          <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-text-muted/60'}`}>·</span>
          <span className={`text-xs animate-pulse ${isDark ? 'text-gray-400' : 'text-text-muted/60'}`}>thinking...</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full animate-bounce ${isDark ? 'bg-white/60' : 'bg-gray-600'}`}
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-text-muted'}`}>Formulating a response...</span>
        </div>
      </div>
    </div>
  );
}

// Conversation sidebar item - Theme-aware
function ConversationItem({ conversation, isActive, onClick, onDelete, onRename, isDark }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(conversation.title);
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      className={`group relative flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${
        isActive
          ? isDark ? 'bg-white/10 text-white border-l-2 border-white/50' : 'bg-gray-100 text-text-primary border-l-2 border-gray-800'
          : isDark ? 'hover:bg-white/5 text-gray-300' : 'hover:bg-bg-tertiary text-text-secondary'
      }`}
      onClick={() => !isEditing && onClick(conversation.id)}
    >
      {isEditing ? (
        <div className="flex-1 flex items-center gap-2">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className={`flex-1 px-3 py-1.5 rounded-lg text-sm outline-none border ${isDark ? 'bg-white/10 text-white border-white/20' : 'bg-bg-card text-text-primary border-gray-400'}`}
            onClick={(e) => e.stopPropagation()}
            autoFocus
          />
          <button onClick={(e) => { e.stopPropagation(); onRename(conversation.id, editTitle); setIsEditing(false); }} className={`${isDark ? 'text-green-400 hover:text-green-300' : 'text-gray-600 hover:text-gray-900'}`}>
            <Check className="w-4 h-4" />
          </button>
          <button onClick={(e) => { e.stopPropagation(); setIsEditing(false); }} className={`${isDark ? 'text-gray-400 hover:text-white' : 'text-text-muted hover:text-text-primary'}`}>
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <>
          <span className="text-sm truncate flex-1">
            {conversation.title || 'New conversation'}
          </span>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <button onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }} className={`p-1.5 rounded-lg ${isDark ? 'hover:bg-white/10' : 'hover:bg-bg-card'}`}>
              <MoreVertical className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-text-muted'}`} />
            </button>
            {showMenu && (
              <div className={`absolute right-2 top-full mt-1 rounded-xl shadow-xl z-50 py-1.5 min-w-[120px] ${isDark ? 'bg-gray-800 border border-white/10' : 'bg-bg-card border border-border-color'}`}>
                <button onClick={(e) => { e.stopPropagation(); setIsEditing(true); setShowMenu(false); }} className={`w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors ${isDark ? 'text-gray-300 hover:bg-white/10 hover:text-white' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}>
                  <Edit2 className="w-3.5 h-3.5" /> Rename
                </button>
                <button onClick={(e) => { e.stopPropagation(); onDelete(conversation.id); setShowMenu(false); }} className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 transition-colors ${isDark ? 'hover:bg-red-500/10' : 'hover:bg-red-50'}`}>
                  <Trash2 className="w-3.5 h-3.5" /> Delete
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ============== MAIN COMPONENT ==============

export default function Chat() {
  const { initialSessionId, onConversationCreated, setActiveSessionId: setParentActiveSessionId } = useOutletContext();
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => initialSessionId || 'session_' + Date.now());

  // Per-message video state (inline display)
  const [messageVideos, setMessageVideos] = useState({});       // {msgId: {path, topic}}
  const [generatingVideos, setGeneratingVideos] = useState({}); // {msgId: {taskId, topic, progress, stage}}

  // Video recommendations based on learning state (3-tier system)
  const [videoRecommendations, setVideoRecommendations] = useState({}); // {msgId: recommendation}
  const [learningState, setLearningState] = useState('initial');

  // Citation/Sources state for RAG
  const [messageSources, setMessageSources] = useState({}); // {msgId: sources[]}

  // Search trail state - tracks which sources were searched
  const [messageSearchTrails, setMessageSearchTrails] = useState({}); // {msgId: {attempts: []}}

  // Web search progress state - shows Perplexity-style searching UI
  const [isWebSearching, setIsWebSearching] = useState(false);
  const [webSearchResults, setWebSearchResults] = useState([]); // Current search results being displayed

  // Clarification request state - when agent needs user help
  const [messageClarifications, setMessageClarifications] = useState({}); // {msgId: {reason, suggestions, searchTrail}}

  // Multimedia content state
  const [messageAnimations, setMessageAnimations] = useState({}); // {msgId: [{videoUrl, status, title, description, code}]}
  const [messageLinkPreviews, setMessageLinkPreviews] = useState({}); // {msgId: [{url, preview, status}]}
  const [messageImages, setMessageImages] = useState({}); // {msgId: [{src, alt, caption}]}

  // Attachment and options state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('pending'); // pending, uploading, processing, completed, error
  const [chatOptions, setChatOptions] = useState(DEFAULT_CHAT_OPTIONS);
  const [showOptions, setShowOptions] = useState(false);

  // Drag-and-drop file upload - dragCounterRef tracks nested enter/leave
  // events from child elements (every element under the cursor fires its
  // own dragenter/dragleave as the pointer crosses it), so the overlay
  // only hides once the drag has actually left the whole drop zone rather
  // than flickering on every child boundary crossed.
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const dragCounterRef = useRef(0);

  // Canvas Panel state
  const [canvasOpen, setCanvasOpen] = useState(false);
  const [canvasDocuments, setCanvasDocuments] = useState([]);
  const [activeCanvasDocId, setActiveCanvasDocId] = useState(null);
  const [highlightedChunkId, setHighlightedChunkId] = useState(null);

  // Audio/Voice state for Socrates TTS
  const [playingMessageId, setPlayingMessageId] = useState(null);
  const [messageAudioUrls, setMessageAudioUrls] = useState({}); // Map message id to audio url
  const [loadingAudioIds, setLoadingAudioIds] = useState(new Set()); // Messages currently loading audio
  const audioRef = useRef(null);

  // Voice input state
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const recognitionRef = useRef(null);

  // Streaming state
  const [streamingMessageId, setStreamingMessageId] = useState(null);
  const [streamingContent, setStreamingContent] = useState('');

  // Agentic workflow state - tracks tool usage, thinking, planning, verification
  const [messageWorkflows, setMessageWorkflows] = useState({});
  const {
    workflowState,
    resetWorkflow,
    handleToolStart,
    handleToolEnd,
    handleComplete: handleWorkflowComplete
  } = useAgenticWorkflow();

  // LLM Model state - null until the user explicitly picks one via the
  // model switcher. Leaving these null (rather than hardcoding a default
  // provider) means the request omits provider/model entirely, and the
  // backend resolves the user's own configured default provider instead -
  // there's no app-wide default to fall back to.
  const [currentLLMProvider, setCurrentLLMProvider] = useState(null);
  const [currentLLMModel, setCurrentLLMModel] = useState(null);
  // Shown when the user tries to send without having explicitly picked a
  // model from the switcher - sendMessage() blocks until one is chosen.
  const [showModelRequiredNotice, setShowModelRequiredNotice] = useState(false);

  // True whenever a conversation is being fetched to restore its messages -
  // without this, the welcome-screen guard below (messages.length === 0) is
  // guaranteed to be true for at least one render while loadConversation's
  // fetch is in flight, flashing the welcome screen on every reopen even
  // though the real messages will load a moment later.
  const [isRestoringConversation, setIsRestoringConversation] = useState(
    () => !!initialSessionId
  );

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const videoPollingRefs = useRef({}); // Store polling intervals by taskId
  const api = useApi();

  // Transcript export/share menu state
  const [shareMenuOpen, setShareMenuOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  const handleExportTranscript = useCallback(async () => {
    try {
      const markdown = await api.get(`/chat/session/${sessionId}/export`);
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${sessionId}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  }, [api, sessionId]);

  const handleShareTranscript = useCallback(async () => {
    setShareLoading(true);
    try {
      const result = await api.post(`/chat/session/${sessionId}/share`, {});
      setShareUrl(`${window.location.origin}/shared/${result.share_token}`);
    } catch (err) {
      console.error('Share failed:', err);
    } finally {
      setShareLoading(false);
    }
  }, [api, sessionId]);

  const handleCopyShareUrl = useCallback(() => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl);
    setShareCopied(true);
    setTimeout(() => setShareCopied(false), 2000);
  }, [shareUrl]);

  useEffect(() => {
    setShareUrl(null);
    setShareMenuOpen(false);
  }, [sessionId]);

  // Theme is now static (single unified Scoratis experience, no more
  // per-subject lookup) - kept as a variable since many places below still
  // reference theme.classes/isDark.
  const theme = useMemo(() => ({
    ...THEME,
    classes: getStandardizedThemeClasses()
  }), []);
  const isDark = false;

  useEffect(() => {
    loadConversations();
    if (initialSessionId) {
      setIsRestoringConversation(true);
      loadConversation(initialSessionId);
    } else {
      setIsRestoringConversation(false);
    }
  }, [initialSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup video polling on unmount
  useEffect(() => {
    return () => {
      Object.values(videoPollingRefs.current).forEach(interval => clearInterval(interval));
    };
  }, []);

  // Initialize voice recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      setVoiceSupported(true);
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setInput(transcript);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // Toggle voice input
  const toggleVoiceInput = useCallback(() => {
    if (!voiceSupported || !recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  }, [isListening, voiceSupported]);

  // Fetch TTS audio for a message
  const fetchTTSAudio = async (messageId, text) => {
    // Mark as loading
    setLoadingAudioIds(prev => new Set([...prev, messageId]));

    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${baseUrl}/chat/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ text })
      });

      if (response.ok) {
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        setMessageAudioUrls(prev => ({ ...prev, [messageId]: audioUrl }));
      }
    } catch (error) {
      console.error('TTS fetch error:', error);
    } finally {
      // Remove from loading
      setLoadingAudioIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(messageId);
        return newSet;
      });
    }
  };

  // Audio playback handlers
  const playAudio = (audioUrl, messageId) => {
    if (audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(e => console.log('Audio playback error:', e));
      setPlayingMessageId(messageId);
    }
  };

  const pauseAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setPlayingMessageId(null);
    }
  };

  // Handle audio end
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      const handleEnded = () => setPlayingMessageId(null);
      audio.addEventListener('ended', handleEnded);
      return () => audio.removeEventListener('ended', handleEnded);
    }
  }, []);

  const loadConversations = async () => {
    try {
      const data = await api.get('/chat/conversations');
      setConversations(data.conversations || []);
      // Also update the sidebar in Dashboard
      if (onConversationCreated) {
        onConversationCreated();
      }
      // No synthetic "ai" greeting message here - the templated Welcome
      // Screen below (portrait/quote/suggestion buttons) already covers
      // this landing state. Injecting a single-message placeholder into
      // `messages` used to make both render at once, each fighting the
      // other for the same flex-1 space (see the messages.length === 0
      // check below).
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (conversationId) => {
    try {
      const data = await api.get(`/chat/conversation/${conversationId}`);
      setActiveConversationId(conversationId);
      // Use the real session_id the backend just returned - share/export
      // (and the chat-stream endpoint itself) key off session_id, not this
      // conversation's numeric id, so a synthesized `conv_${id}` string
      // would never match the row in the conversations table.
      setSessionId(data.session_id || `conv_${conversationId}`);
      setMessages(data.messages?.map(m => ({
        ...m,
        timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      })) || []);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setIsRestoringConversation(false);
    }
  };

  const startNewConversation = () => {
    setActiveConversationId(null);
    setSessionId('session_' + Date.now());
    setIsRestoringConversation(false);
    // Empty, not a synthetic greeting message - see the comment in
    // loadConversations() above for why.
    setMessages([]);
    inputRef.current?.focus();
  };

  const deleteConversation = async (conversationId) => {
    try {
      await api.delete(`/chat/conversation/${conversationId}`);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      if (activeConversationId === conversationId) startNewConversation();
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  const renameConversation = async (conversationId, newTitle) => {
    try {
      await api.put(`/chat/conversation/${conversationId}`, { title: newTitle });
      setConversations(prev => prev.map(c => c.id === conversationId ? { ...c, title: newTitle } : c));
    } catch (error) {
      console.error('Failed to rename:', error);
    }
  };

  // ============== INLINE VIDEO GENERATION ==============

  // Start video generation linked to a specific message
  const startVideoGeneration = async (messageId, suggestion) => {
    try {
      const response = await api.post('/videos/generate', {
        topic: suggestion.suggested_topic,
        quality: 'high'
      });

      // Track video generation for this message
      setGeneratingVideos(prev => ({
        ...prev,
        [messageId]: {
          taskId: response.task_id,
          topic: suggestion.suggested_topic,
          progress: 5,
          stage: 'content'
        }
      }));

      // Start polling for this task
      pollVideoStatus(response.task_id, messageId, suggestion.suggested_topic);
    } catch (error) {
      console.error('Failed to start video generation:', error);
    }
  };

  // Poll video status and update per-message state
  // manim renders can legitimately take up to 25 minutes (see the backend's
  // own subprocess timeout in tasks/video_tasks.py) - this poll timeout must
  // stay comfortably above that so a slow-but-healthy render never gets
  // mislabeled as stuck. 900 polls @ 2s = 30 minutes.
  const MAX_VIDEO_POLLS = 900;

  const stopVideoPolling = (taskId, messageId, errorMessage) => {
    clearInterval(videoPollingRefs.current[taskId]);
    delete videoPollingRefs.current[taskId];
    setGeneratingVideos(prev => {
      if (!prev[messageId]) return prev;
      return {
        ...prev,
        [messageId]: { ...prev[messageId], error: errorMessage }
      };
    });
  };

  const pollVideoStatus = (taskId, messageId, topic) => {
    let pollCount = 0;
    videoPollingRefs.current[taskId] = setInterval(async () => {
      pollCount += 1;
      if (pollCount > MAX_VIDEO_POLLS) {
        stopVideoPolling(taskId, messageId, 'This is taking longer than expected. Check back later - the video may still finish in the background.');
        return;
      }

      try {
        const status = await api.get(`/videos/status/${taskId}`);

        // Update generating state for this message
        setGeneratingVideos(prev => {
          if (!prev[messageId]) return prev;
          return {
            ...prev,
            [messageId]: {
              ...prev[messageId],
              progress: status.progress || 0,
              stage: status.stage || 'content'
            }
          };
        });

        // Check for completion
        if (status.status === 'completed') {
          clearInterval(videoPollingRefs.current[taskId]);
          delete videoPollingRefs.current[taskId];

          // Move from generating to completed
          setGeneratingVideos(prev => {
            const updated = { ...prev };
            delete updated[messageId];
            return updated;
          });
          setMessageVideos(prev => ({
            ...prev,
            [messageId]: {
              path: status.video_path,
              topic: topic
            }
          }));
        } else if (status.status === 'error') {
          stopVideoPolling(taskId, messageId, status.error || 'Video generation failed for an unknown reason.');
        }
      } catch (error) {
        console.error('Failed to poll video status:', error);
        // Stop polling on error (e.g., 404 Not Found means task doesn't exist)
        if (error.response?.status === 404 || error.message?.includes('404')) {
          stopVideoPolling(taskId, messageId, 'Lost track of this video job.');
        }
      }
    }, 2000);
  };

  // Remove video from a specific message
  const removeMessageVideo = (messageId) => {
    setMessageVideos(prev => {
      const updated = { ...prev };
      delete updated[messageId];
      return updated;
    });
    // Also clears a failed/timed-out generation card, which lives in
    // generatingVideos rather than messageVideos (a completed video never
    // has an entry here, so this is a no-op in that case).
    setGeneratingVideos(prev => {
      if (!prev[messageId]) return prev;
      const updated = { ...prev };
      delete updated[messageId];
      return updated;
    });
  };

  // Handle accepting a video recommendation - uses new /chat/generate-video endpoint
  const handleAcceptVideoOffer = async (recommendation, messageId) => {
    if (!recommendation?.available || !messageId) return;

    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${baseUrl}/chat/generate-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          session_id: sessionId,
          custom_topic: recommendation.topic  // Optional override
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.task_id) {
          setGeneratingVideos(prev => ({
            ...prev,
            [messageId]: {
              taskId: data.task_id,
              topic: data.topic,
              progress: 5,
              stage: 'content'
            }
          }));
          pollVideoStatus(data.task_id, messageId, data.topic);

          // Remove the recommendation
          setVideoRecommendations(prev => {
            const updated = { ...prev };
            delete updated[messageId];
            return updated;
          });
        }
      } else {
        const errorData = await response.json();
        console.error('Video generation failed:', errorData.detail);
      }
    } catch (error) {
      console.error('Failed to generate video:', error);
    }
  };

  // Handle dismissing a video recommendation
  const handleDismissVideoOffer = (messageId) => {
    setVideoRecommendations(prev => {
      const updated = { ...prev };
      delete updated[messageId];
      return updated;
    });
  };

  // Fetch documents for canvas panel
  const fetchCanvasDocuments = useCallback(async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${baseUrl}/v1/documents?status=COMPLETED`, {
        headers: { ...getAuthHeaders() },
      });
      if (response.ok) {
        const data = await response.json();
        setCanvasDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Failed to fetch documents for canvas:', error);
    }
  }, []);

  // Load documents when canvas opens
  useEffect(() => {
    if (canvasOpen) {
      fetchCanvasDocuments();
    }
  }, [canvasOpen, fetchCanvasDocuments]);

  // Handle citation click - open canvas and highlight chunk
  const handleCitationClick = useCallback((source) => {
    if (source?.document_id) {
      setActiveCanvasDocId(source.document_id);
      setHighlightedChunkId(source.chunk_id);
      setCanvasOpen(true);
    }
  }, []);

  const sendMessage = async (customMessage = null) => {
    // A file attached with no typed text used to silently do nothing here -
    // content was '', so this returned before the request ever fired, with
    // no error or feedback. The backend's /chat/with-attachment also
    // requires a non-empty message, so substitute a sensible default rather
    // than just bypassing this check.
    const content = customMessage || input.trim() || (selectedFile ? `Please analyze this document: ${selectedFile.name}` : '');
    if (!content || loading) return;

    if (!currentLLMModel) {
      setShowModelRequiredNotice(true);
      return;
    }

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    // The textarea auto-grows via an inline style set imperatively in its
    // onInput handler below (not through React), so clearing the `input`
    // state alone doesn't shrink it back down - once you've typed a longer
    // message, the box stays visually oversized on every message after,
    // even though it's empty. Reset the DOM node's own height directly.
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
    setLoading(true);

    const newMessageId = Date.now() + 1;

    // Create a placeholder message for streaming
    setMessages(prev => [...prev, {
      id: newMessageId,
      role: 'ai',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
    setStreamingMessageId(newMessageId);
    setStreamingContent('');
    resetWorkflow(); // Reset agentic workflow for new message

    // Show web search progress if enabled
    if (chatOptions.useWebSearch) {
      setIsWebSearching(true);
      setWebSearchResults([]);
    }

    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      let response;

      // If file is attached, use multipart form data
      if (selectedFile) {
        setUploadStatus('uploading');
        const formData = new FormData();
        formData.append('message', content);
        formData.append('session_id', sessionId);
        formData.append('file', selectedFile);
        formData.append('use_web_search', chatOptions.useWebSearch);
        formData.append('use_reasoning', chatOptions.useReasoning);
        if (currentLLMProvider) formData.append('provider', currentLLMProvider);
        if (currentLLMModel) formData.append('model', currentLLMModel);

        response = await fetchWithAuthRetry(`${baseUrl}/chat/with-attachment`, {
          method: 'POST',
          headers: { ...getAuthHeaders() },
          body: formData
        });

        // Clear file after sending
        setSelectedFile(null);
        setUploadStatus('pending');
        setUploadProgress(0);
      } else {
        // Regular JSON request with chat options and selected LLM
        response = await fetchWithAuthRetry(`${baseUrl}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({
            message: content,
            session_id: sessionId,
            use_web_search: chatOptions.useWebSearch,
            use_reasoning: chatOptions.useReasoning,
            provider: currentLLMProvider,
            model: currentLLMModel
          })
        });
      }

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Your session expired and could not be renewed - please log in again.');
        }
        throw new Error('Stream request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              // Handle sources event (streamed before LLM response)
              if (data.type === 'sources' && data.sources) {
                setMessageSources(prev => ({
                  ...prev,
                  [newMessageId]: data.sources
                }));
                continue;
              }

              // Handle search trail event - shows which sources were searched
              if (data.type === 'search_trail' && data.search_trail) {
                setMessageSearchTrails(prev => ({
                  ...prev,
                  [newMessageId]: data.search_trail
                }));

                // Extract web search results for Perplexity-style display
                const webSearchAttempt = data.search_trail.attempts?.find(a => a.source === 'web_search');
                if (webSearchAttempt?.results) {
                  setWebSearchResults(webSearchAttempt.results);
                }
                continue;
              }

              // Handle clarification request - when agent needs user help
              if (data.type === 'clarification_request') {
                setMessageClarifications(prev => ({
                  ...prev,
                  [newMessageId]: {
                    reason: data.reason,
                    suggestions: data.suggestions || [],
                    searchTrail: data.search_trail || []
                  }
                }));
                continue;
              }

              // Handle Manim animation events
              if (data.type === 'manim_animation') {
                setMessageAnimations(prev => ({
                  ...prev,
                  [newMessageId]: [
                    ...(prev[newMessageId] || []),
                    {
                      videoUrl: data.video_url,
                      thumbnailUrl: data.thumbnail_url,
                      title: data.title,
                      description: data.description,
                      code: data.code,
                      status: data.status || 'ready'
                    }
                  ]
                }));
                continue;
              }

              // Handle link preview events
              if (data.type === 'link_preview') {
                setMessageLinkPreviews(prev => ({
                  ...prev,
                  [newMessageId]: [
                    ...(prev[newMessageId] || []),
                    {
                      url: data.url,
                      preview: data.preview,
                      status: data.status || 'ready',
                      error: data.error
                    }
                  ]
                }));
                continue;
              }

              // Handle display image events
              if (data.type === 'display_image') {
                setMessageImages(prev => ({
                  ...prev,
                  [newMessageId]: [
                    ...(prev[newMessageId] || []),
                    {
                      src: data.src,
                      alt: data.alt,
                      caption: data.caption
                    }
                  ]
                }));
                continue;
              }

              // Handle agentic tool events
              if (data.type === 'tool_start') {
                handleToolStart(data.tool, data.args);
                // Store workflow state for this message - compute new state directly
                setMessageWorkflows(prev => {
                  const currentWorkflow = prev[newMessageId] || { steps: [], hasTools: false };
                  return {
                    ...prev,
                    [newMessageId]: {
                      ...currentWorkflow,
                      hasTools: true,
                      steps: [...(currentWorkflow.steps || []), { tool: data.tool, args: data.args, complete: false }],
                      activeStep: { tool: data.tool, args: data.args }
                    }
                  };
                });
                continue;
              }

              if (data.type === 'tool_end') {
                handleToolEnd(data.tool, data.result);
                // Update workflow state - mark tool as complete
                setMessageWorkflows(prev => {
                  const currentWorkflow = prev[newMessageId] || { steps: [], hasTools: false };
                  return {
                    ...prev,
                    [newMessageId]: {
                      ...currentWorkflow,
                      steps: (currentWorkflow.steps || []).map(s =>
                        s.tool === data.tool && !s.complete
                          ? { ...s, complete: true, result: data.result }
                          : s
                      ),
                      activeStep: null
                    }
                  };
                });
                continue;
              }

              // Handle phase changes
              if (data.type === 'phase') {
                setMessageWorkflows(prev => ({
                  ...prev,
                  [newMessageId]: { ...prev[newMessageId], phase: data.phase }
                }));
                continue;
              }

              // Handle thinking events (agent reasoning)
              if (data.type === 'thinking') {
                setMessageWorkflows(prev => ({
                  ...prev,
                  [newMessageId]: {
                    ...prev[newMessageId],
                    hasTools: true,
                    thinking: {
                      thought: data.content,
                      confidence: data.confidence
                    }
                  }
                }));
                continue;
              }

              if (data.chunk) {
                fullContent += data.chunk;
                // Update the message content in real-time
                setMessages(prev => prev.map(msg =>
                  msg.id === newMessageId
                    ? { ...msg, content: fullContent }
                    : msg
                ));
              }

              if (data.done) {
                // The agentic path can reach "done" having never streamed a
                // single token event (e.g. every iteration used a tool, or
                // the model call failed and fell back to a canned apology
                // sent only in this final payload) - data.chunk is always ''
                // on this event, so fullContent above would otherwise stay
                // empty forever and the message renders as literally
                // nothing, even though the backend sent real text.
                if (!fullContent && (data.formatted_response || data.full_response)) {
                  fullContent = data.formatted_response || data.full_response;
                  setMessages(prev => prev.map(msg =>
                    msg.id === newMessageId
                      ? { ...msg, content: fullContent }
                      : msg
                  ));
                }

                // Mark agentic workflow complete
                handleWorkflowComplete();
                setMessageWorkflows(prev => ({
                  ...prev,
                  [newMessageId]: { ...workflowState, isComplete: true }
                }));

                // Handle completion with metadata
                if (data.conversation_id) {
                  setActiveConversationId(data.conversation_id);
                  loadConversations();
                }

                // Update learning state
                if (data.learning_state) {
                  setLearningState(data.learning_state);
                }

                // Fetch TTS audio for the completed message
                if (fullContent && fullContent.trim()) {
                  fetchTTSAudio(newMessageId, fullContent);
                }

                // NEW: Handle AUTOMATIC video generation
                if (data.auto_video) {
                  const { task_id, topic, concepts, visualization_type, estimated_duration } = data.auto_video;

                  // Add to generatingVideos state immediately
                  setGeneratingVideos(prev => ({
                    ...prev,
                    [newMessageId]: {
                      taskId: task_id,
                      topic: topic,
                      concepts: concepts || [],
                      progress: 5,
                      stage: 'content',
                      estimatedDuration: estimated_duration,
                      autoGenerated: true
                    }
                  }));

                  // Start polling for this auto-generated video
                  pollVideoStatus(task_id, newMessageId, topic);

                  console.log(`Auto-generating video: ${topic}`);
                }
                // Fallback: Handle manual video offer (only if not auto-generating)
                else if (data.video_available && !data.auto_video) {
                  // Store video offer for user to trigger manually
                  setVideoRecommendations(prev => ({
                    ...prev,
                    [newMessageId]: {
                      available: true,
                      topic: data.video_topic,
                      concepts: data.video_concepts || [],
                      type: data.video_type
                    }
                  }));
                }
              }
            } catch (e) {
              // Skip malformed JSON lines
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      // Update message with error - surface a real session-expiry message
      // when that's actually what happened, instead of always blaming "the
      // AI" for what's really an auth problem (see fetchWithAuthRetry above).
      const errorText = error?.message?.includes('session expired')
        ? error.message
        : "I apologize, but I encountered an error. Please try again.";
      setMessages(prev => prev.map(msg =>
        msg.id === newMessageId
          ? { ...msg, content: errorText }
          : msg
      ));
    } finally {
      setLoading(false);
      setStreamingMessageId(null);
      setStreamingContent('');
      // Reset web search state after completion
      setIsWebSearching(false);
      setWebSearchResults([]);
    }
  };

  // Drag-and-drop handlers for the whole chat area - reuses the exact same
  // selectedFile/uploadStatus state the "+" attach button sets, so a
  // dropped file flows into the same chat_with_attachment upload+RAG
  // pipeline with no backend changes needed.
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!e.dataTransfer?.types?.includes('Files')) return;
    dragCounterRef.current += 1;
    setIsDraggingFile(true);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      dragCounterRef.current = 0;
      setIsDraggingFile(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = 0;
    setIsDraggingFile(false);

    const file = e.dataTransfer?.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadStatus('pending');
      inputRef.current?.focus();
    }
  };

  return (
    <div className="relative h-full w-full flex flex-col">
      <div className="flex-1 flex relative overflow-hidden">
      {/* Main Chat Area */}
      <div
        className="flex-1 flex flex-col min-w-0 min-h-0 relative"
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {isDraggingFile && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#6b7c5e]/10 backdrop-blur-sm border-4 border-dashed border-[#6b7c5e] rounded-2xl m-3 pointer-events-none">
            <div className="flex flex-col items-center gap-3 px-8 py-6 rounded-2xl bg-white/95 shadow-xl">
              <FileText className="w-10 h-10 text-[#6b7c5e]" />
              <p className="text-lg font-medium text-[#4a5a40]">Drop your file to attach it</p>
              <p className="text-sm text-gray-500">PDF, Word, text, Markdown, or images</p>
            </div>
          </div>
        )}
        {/* Header - Large with themed gradient background (no hotlinked
            image - a third-party photo host here previously caused broken/
            cert-blocked loads on networks that intercept or block image
            CDNs, same reasoning as TUTOR.portrait below) */}
        <div
          className={`relative h-32 flex items-center justify-between px-6 shadow-lg ${THEME.classes.headerBg}`}
        >

          {/* Header content - Left side */}
          <div className="relative z-50 flex items-center gap-4">
                {/* Tutor portrait - larger */}
                <div className="w-16 h-16 rounded-full overflow-hidden border-3 border-white/70 shadow-xl flex-shrink-0">
                  <img
                    src={TUTOR.portrait}
                    alt={TUTOR.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      if (e.target.src.endsWith('/socrates-nobg.png')) { e.target.style.display = 'none'; return; }
                      e.target.src = '/socrates-nobg.png';
                    }}
                  />
                </div>
                <div className="flex flex-col">
                  <span className="font-semibold text-xl text-white drop-shadow-md">
                    {TUTOR.name}
                  </span>
                  <span className="text-sm text-white/90">
                    {TUTOR.title}
                  </span>
                </div>

                {/* LLM Model Switcher - Left side */}
                <div className="ml-4">
                  <LLMSwitcher
                    currentProvider={currentLLMProvider}
                    currentModel={currentLLMModel}
                    onModelChange={(provider, model) => {
                      setCurrentLLMProvider(provider);
                      setCurrentLLMModel(model);
                      setShowModelRequiredNotice(false);
                    }}
                  />
                </div>

          </div>

          {/* Right side - Loading indicator and Canvas toggle */}
          <div className="relative z-10 flex items-center gap-3">
            {loading && (
              <div className="flex items-center gap-2 text-white opacity-90">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm font-medium">Thinking...</span>
              </div>
            )}
            {/* Canvas Panel Toggle */}
            <CanvasToggleButton
              isOpen={canvasOpen}
              onClick={() => setCanvasOpen(!canvasOpen)}
              documentCount={canvasDocuments.length}
            />

            {/* Export / Share transcript */}
            <div className="relative">
              <button
                onClick={() => setShareMenuOpen((v) => !v)}
                title="Export or share this conversation"
                className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
              >
                <Share2 className="w-4 h-4" />
              </button>
              {shareMenuOpen && (
                <div className="absolute right-0 top-11 z-50 w-72 bg-bg-card border border-border-color rounded-xl shadow-2xl p-3 text-text-primary">
                  <button
                    onClick={handleExportTranscript}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-accent-olive/10 text-sm text-left"
                  >
                    <Download className="w-4 h-4 text-accent-olive" />
                    Download transcript (.md)
                  </button>
                  {!shareUrl ? (
                    <button
                      onClick={handleShareTranscript}
                      disabled={shareLoading}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-accent-olive/10 text-sm text-left disabled:opacity-50"
                    >
                      {shareLoading ? (
                        <Loader2 className="w-4 h-4 text-accent-olive animate-spin" />
                      ) : (
                        <Link2 className="w-4 h-4 text-accent-olive" />
                      )}
                      Create shareable link
                    </button>
                  ) : (
                    <div className="px-3 py-2">
                      <div className="text-xs text-text-muted mb-1.5">Anyone with this link can view this conversation:</div>
                      <div className="flex items-center gap-2 bg-bg-tertiary rounded-lg px-2 py-1.5">
                        <input
                          readOnly
                          value={shareUrl}
                          className="flex-1 bg-transparent text-xs text-text-secondary outline-none truncate"
                          onFocus={(e) => e.target.select()}
                        />
                        <button onClick={handleCopyShareUrl} title="Copy link" className="text-text-muted hover:text-accent-olive">
                          {shareCopied ? <Check className="w-4 h-4 text-accent-olive" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages - only rendered when there's something to show. Previously
            this always rendered alongside the welcome screen below (both
            flex-1 siblings whenever messages.length === 0), splitting the
            available height 50/50 with an empty div. That squeezed the
            welcome screen into half the space it needed, and its
            overflow-y-auto + items-center combination clipped the portrait
            (the first, topmost element in the centered stack) into
            unreachable negative-scroll space - a well-known CSS interaction,
            not a broken image. Making these two blocks mutually exclusive
            gives the welcome screen its full space back. */}
        {(messages.length > 0 || isRestoringConversation) && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="space-y-0">
            {messages.map((msg, i) => (
              <MessageCard
                key={msg.id}
                message={msg}
                index={i}
                audioUrl={messageAudioUrls[msg.id]}
                isCurrentlyPlaying={playingMessageId === msg.id}
                isLoadingAudio={loadingAudioIds.has(msg.id)}
                onPlayAudio={playAudio}
                onPauseAudio={pauseAudio}
                video={messageVideos[msg.id]}
                generatingVideo={generatingVideos[msg.id]}
                onRemoveVideo={() => removeMessageVideo(msg.id)}
                videoRecommendation={videoRecommendations[msg.id]}
                onAcceptVideo={handleAcceptVideoOffer}
                onDismissVideo={handleDismissVideoOffer}
                workflow={messageWorkflows[msg.id] || (msg.id === streamingMessageId ? workflowState : null)}
                theme={theme}
                sources={messageSources[msg.id]}
                onCitationClick={handleCitationClick}
                searchTrail={messageSearchTrails[msg.id]}
                clarification={messageClarifications[msg.id]}
                animations={messageAnimations[msg.id]}
                linkPreviews={messageLinkPreviews[msg.id]}
                images={messageImages[msg.id]}
                onSuggestionClick={(suggestion) => {
                  setInput(suggestion);
                  inputRef.current?.focus();
                }}
              />
            ))}

            {/* Perplexity-style Web Search Progress - shows while searching */}
            {isWebSearching && loading && (
              <div className={`py-6 ${isDark ? 'bg-white/5' : 'bg-bg-secondary/50'}`}>
                <div className="max-w-3xl mx-auto px-6">
                  {/* Use dark or light variant based on theme */}
                  {isDark ? (
                    <WebSearchProgress
                      isSearching={webSearchResults.length === 0}
                      searchResults={webSearchResults}
                      query={input}
                      theme={theme}
                    />
                  ) : (
                    <WebSearchProgressLight
                      isSearching={webSearchResults.length === 0}
                      searchResults={webSearchResults}
                      query={input}
                      theme={theme}
                    />
                  )}

                  {/* Show "Generating response" after sources are found */}
                  {webSearchResults.length > 0 && (
                    <div className={`flex items-center gap-3 mt-4 pt-4 border-t ${isDark ? 'border-white/10' : 'border-gray-200/50'}`}>
                      <div className="flex gap-1.5">
                        {[...Array(3)].map((_, i) => (
                          <div
                            key={i}
                            className={`w-2 h-2 rounded-full animate-bounce ${isDark ? 'bg-blue-400' : 'bg-[#6b7c5e]'}`}
                            style={{ animationDelay: `${i * 150}ms` }}
                          />
                        ))}
                      </div>
                      <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {TUTOR.name} is formulating a response...
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {loading && !isWebSearching && <TypingIndicator theme={theme} isDark={isDark} />}
            <div ref={messagesEndRef} />
          </div>
        </div>
        )}

        {/* Welcome screen - Theme-aware centered design with tutor portrait */}
        {messages.length === 0 && !isRestoringConversation && (
            <div className="flex-1 min-h-0 overflow-y-auto flex items-center justify-center p-8">
              <div className="text-center max-w-lg">
                {/* Tutor portrait */}
                <div className="flex justify-center mb-6">
                  <div className="relative">
                    <div className={`w-36 h-36 rounded-full overflow-hidden shadow-2xl border-4 ring-4 ${isDark ? 'border-white/30 ring-white/10' : 'border-white/90 ring-gray-200'}`}>
                      <img
                        src={TUTOR.portrait}
                        alt={TUTOR.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          if (e.target.src.endsWith('/socrates-nobg.png')) { e.target.style.display = 'none'; return; }
                          e.target.src = '/socrates-nobg.png';
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Tutor name and title */}
                <h2 className={`text-2xl font-medium mb-1 ${isDark ? 'text-white' : 'text-text-primary'}`}
                    style={{ fontFamily: 'Georgia, serif' }}>
                  {TUTOR.name}
                </h2>
                <p className={`text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                  {TUTOR.title}
                </p>
                <p className={`text-xs mb-4 ${isDark ? 'text-gray-400' : 'text-text-muted/70'}`}>
                  {TUTOR.years}
                </p>

                <h1 className={`text-xl font-light mb-2 ${isDark ? 'text-white' : 'text-text-primary'}`}
                    style={{ fontFamily: 'Georgia, serif' }}>
                  Welcome to Scoratis
                </h1>

                {/* Tutor quote */}
                <p className={`text-base mb-8 italic px-4 ${isDark ? 'text-gray-300' : 'text-text-muted'}`}>
                  {TUTOR.quote}
                </p>

                <div className="space-y-3">
                  {[
                    { label: 'Explore a concept', prompt: 'Help me understand the concept of recursion in programming.' },
                    { label: 'Challenge my thinking', prompt: 'Challenge my assumptions about the nature of consciousness.' },
                    { label: 'Guide my learning', prompt: 'Guide me through studying the basics of quantum mechanics.' },
                    { label: 'Help me understand', prompt: 'Ask me Socratic questions about the causes of World War I.' }
                  ].map((item, i) => (
                    <button
                      key={i}
                      onClick={() => { setInput(item.prompt); inputRef.current?.focus(); }}
                      className={`w-full text-left px-5 py-4 rounded-xl border transition-all text-base
                        ${isDark
                          ? 'border-white/20 hover:border-white/40 hover:bg-white/10 text-gray-300 hover:text-white'
                          : 'border-[#D4CFB8] hover:border-gray-800 hover:bg-gray-50 text-text-secondary hover:text-text-primary'
                        }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
        )}

        {/* Input area - Theme-aware floating bar */}
        <div className={`flex-shrink-0 pt-4 pb-6 ${isDark ? 'bg-gradient-to-t from-black/60 via-black/30 to-transparent' : 'bg-gradient-to-t from-white/80 via-white/60 to-transparent'}`}>
          <div className="max-w-3xl mx-auto px-4">
            {/* File Preview (when file selected) */}
            {selectedFile && (
              <div className={`mb-3 backdrop-blur-sm rounded-2xl p-3 shadow-sm ${isDark ? 'bg-white/10 border border-white/20' : 'bg-white/90 border border-gray-200/50'}`}>
                <AttachmentPreview
                  file={selectedFile}
                  uploadProgress={uploadProgress}
                  uploadStatus={uploadStatus}
                  onRemove={() => {
                    setSelectedFile(null);
                    setUploadStatus('pending');
                    setUploadProgress(0);
                  }}
                />
              </div>
            )}

            {/* Model-required notice - shown when the user tries to send
                without having explicitly picked a model from the switcher */}
            {showModelRequiredNotice && (
              <div className="mb-3 flex items-center gap-2 px-4 py-3 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-sm">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>Please select a model above before starting a chat.</span>
              </div>
            )}

            {/* Main input container - Theme-aware */}
            <div className={`relative backdrop-blur-xl rounded-3xl shadow-lg transition-all duration-200
                            ${isDark
                              ? 'bg-white/10 border border-white/20 hover:bg-white/15 hover:border-white/30'
                              : 'bg-white/95 border border-gray-200/60 hover:shadow-xl hover:border-gray-300/80'
                            }
                            ${loading ? 'opacity-75' : ''}`}>

              {/* Top row - Options pills - Athenian themed */}
              <div className="flex items-center gap-3 px-5 pt-4 pb-2 border-b border-[#D4CFB8]/30">
                <button
                  onClick={() => setChatOptions(prev => ({ ...prev, useWebSearch: !prev.useWebSearch }))}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200
                    ${chatOptions.useWebSearch
                      ? 'text-[#4a5a40] bg-[#6b7c5e]/15 border border-[#6b7c5e]/40 shadow-sm'
                      : 'text-gray-500 hover:text-[#4a5a40] hover:bg-[#6b7c5e]/5 border border-transparent'}`}
                  title="Web Search"
                >
                  <Globe className={`w-4 h-4 ${chatOptions.useWebSearch ? 'text-[#6b7c5e]' : ''}`} />
                  <span className="hidden sm:inline">Search</span>
                </button>

                <button
                  onClick={() => setChatOptions(prev => ({ ...prev, useReasoning: !prev.useReasoning }))}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200
                    ${chatOptions.useReasoning
                      ? 'text-[#4a5a40] bg-[#6b7c5e]/15 border border-[#6b7c5e]/40 shadow-sm'
                      : 'text-gray-500 hover:text-[#4a5a40] hover:bg-[#6b7c5e]/5 border border-transparent'}`}
                  title="Deep Thinking"
                >
                  <Brain className={`w-4 h-4 ${chatOptions.useReasoning ? 'text-[#6b7c5e]' : ''}`} />
                  <span className="hidden sm:inline">Think</span>
                </button>

                <div className="flex-1" />

                {/* Video generation hint */}
                <button
                  onClick={() => {
                    if (input.trim()) {
                      sendMessage(input.trim() + ' [Please explain this visually with a video]');
                    }
                  }}
                  disabled={loading || !input.trim()}
                  className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 text-gray-400 hover:text-[#4a5a40] hover:bg-[#6b7c5e]/5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-gray-400"
                  title="Generate visual explanation"
                >
                  <Film className="w-4 h-4" />
                  <span className="hidden md:inline">Video</span>
                </button>
              </div>

              {/* Bottom row - Input area */}
              <div className="flex items-end gap-3 p-4">
                {/* Attachment button */}
                <button
                  onClick={() => document.getElementById('gemini-file-input')?.click()}
                  disabled={loading || uploadStatus === 'uploading'}
                  className="flex-shrink-0 w-11 h-11 rounded-full flex items-center justify-center transition-all disabled:opacity-40 text-gray-500 hover:text-[#4a5a40] hover:bg-[#6b7c5e]/10"
                  title="Attach file"
                >
                  <Plus className="w-6 h-6" />
                </button>
                <input
                  id="gemini-file-input"
                  type="file"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setSelectedFile(file);
                      setUploadStatus('pending');
                    }
                    e.target.value = '';
                  }}
                />

                {/* Text input */}
                <div className="flex-1 min-w-0">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    placeholder="Ask a question..."
                    className="w-full bg-transparent text-lg leading-7 outline-none resize-none min-h-[32px] max-h-40 text-gray-800 placeholder-gray-400"
                    rows={1}
                    disabled={loading}
                    onInput={(e) => {
                      e.target.style.height = 'auto';
                      e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
                    }}
                  />
                </div>

                {/* Right side buttons */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Voice input button */}
                  {voiceSupported && (
                    <button
                      onClick={toggleVoiceInput}
                      disabled={loading}
                      className={`w-11 h-11 rounded-full flex items-center justify-center transition-all disabled:opacity-40
                        ${isListening
                          ? 'bg-red-500 text-white animate-pulse'
                          : 'text-gray-500 hover:text-[#4a5a40] hover:bg-[#6b7c5e]/10'
                        }`}
                      title={isListening ? 'Stop listening' : 'Voice input'}
                    >
                      {isListening ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
                    </button>
                  )}

                  {/* Send button */}
                  <button
                    onClick={() => sendMessage()}
                    disabled={loading || (!input.trim() && !selectedFile)}
                    className={`w-12 h-12 rounded-full flex items-center justify-center transition-all
                      ${(input.trim() || selectedFile) && !loading
                        ? 'bg-[#6b7c5e] hover:bg-[#5a6c4e] text-white shadow-md hover:shadow-lg hover:scale-105'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      } disabled:opacity-40`}
                    title="Send message"
                  >
                    {loading ? (
                      <Loader2 className="w-6 h-6 animate-spin" />
                    ) : (
                      <ArrowUp className={`w-6 h-6 ${(input.trim() || selectedFile) ? 'text-white' : ''}`} />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Subtle hint text */}
            <p className={`text-center text-xs mt-2 ${isDark ? 'text-gray-400' : 'text-gray-400'}`}>
              Socratic learning powered by AI
            </p>
          </div>
        </div>
      </div>

      {/* Hidden Audio Element for TTS Playback */}
      <audio ref={audioRef} preload="none" className="hidden" />

      {/* Canvas Panel - Document preview sidebar */}
      <CanvasPanel
        isOpen={canvasOpen}
        onClose={() => setCanvasOpen(false)}
        onToggle={() => setCanvasOpen(!canvasOpen)}
        documents={canvasDocuments}
        activeDocumentId={activeCanvasDocId}
        onSelectDocument={setActiveCanvasDocId}
        highlightedChunkId={highlightedChunkId}
        onOpenDocument={handleCitationClick}
      />
    </div>
    </div>
  );
}
