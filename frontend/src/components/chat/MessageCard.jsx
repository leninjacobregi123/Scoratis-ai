import React, { useState, useMemo, useCallback, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  Loader2, Pause, Volume2, Film, FileText 
} from 'lucide-react';
import { 
  getSubjectTutor, getSubjectImage, isDarkTheme, DEFAULT_THEME 
} from '../../config/subjectThemes';
import { parseCitations, buildSourceMap } from '../../utils/citations';
import GuardrailCard from './GuardrailCard';
import AgenticWorkflow from '../AgenticWorkflow';
import { SearchTrailIndicator } from '../SearchTrailIndicator';
import { ThinkingDropdown, ThinkingDropdownLight } from '../ThinkingDropdown';
import ClarificationRequest from '../ClarificationRequest';
import ManimAnimationCard from '../ManimAnimationCard';
import { LinkPreviewGrid } from '../LinkPreviewCard';
import { ImageGallery } from '../InlineImage';
import SoundWaveAnimation from './SoundWaveAnimation';
import InlineVideoCard from './InlineVideoCard';
import VideoOfferCard from './VideoOfferCard';

const stripPedagogicalPlan = (content) => {
  if (!content) return content;
  return content
    .replace(/<pedagogical_plan>[\s\S]*?<\/pedagogical_plan>/gi, '')
    .replace(/\*\*<pedagogical_plan>\*\*[\s\S]*?<\/pedagogical_plan>/gi, '')
    .trim();
};

export default function MessageCard({
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
  subjectId,
  sources,
  workflow,
  guardrailInfo,
  onSwitchSubject,
  onCitationClick,
  searchTrail,
  clarification,
  animations,
  linkPreviews,
  images,
  thinking,
  isStreaming,
  onSuggestionClick
}) {
  const isUser = message.role === 'user';
  const [isVisible, setIsVisible] = useState(false);
  const [showVideoOffer, setShowVideoOffer] = useState(false);
  const [showSourcesList, setShowSourcesList] = useState(false);

  const tutor = useMemo(() => getSubjectTutor(subjectId), [subjectId]);
  const t = theme || DEFAULT_THEME;
  const avatarImage = tutor?.portrait || getSubjectImage(subjectId, 'avatar');
  const strippedContent = isUser ? message.content : stripPedagogicalPlan(message.content);

  const sourceMap = useMemo(() => buildSourceMap(sources), [sources]);

  const { cleanContent, citations } = useMemo(() => {
    if (isUser || !strippedContent) {
      return { cleanContent: strippedContent, citations: [] };
    }
    return parseCitations(strippedContent);
  }, [strippedContent, isUser]);

  const displayContent = citations.length > 0 ? cleanContent : strippedContent;

  useEffect(() => {
    if (videoRecommendation && !video && !generatingVideo) {
      setShowVideoOffer(true);
    }
  }, [videoRecommendation, video, generatingVideo]);

  const handleAcceptVideo = () => {
    setShowVideoOffer(false);
    if (onAcceptVideo) onAcceptVideo(videoRecommendation, message.id);
  };

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
        <div className={`flex items-center gap-3 mb-4 ${isUser ? 'justify-end' : ''}`}>
          {!isUser && avatarImage && (
            <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-gray-300 shadow-md flex-shrink-0">
              <img
                src={avatarImage}
                alt={tutor?.name || 'Scoratis'}
                className="w-full h-full object-cover"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </div>
          )}
          <div className={`flex flex-col ${isUser ? 'items-end' : ''}`}>
            <span className={`text-sm font-medium ${isUser ? 'text-text-muted' : t.classes.aiMsgAccent}`}>
              {isUser ? 'You' : tutor?.name || 'Scoratis'}
            </span>
            {!isUser && tutor?.title && (
              <span className="text-xs text-text-muted/70">{tutor.title}</span>
            )}
          </div>
          <span className="text-xs text-text-muted/60">·</span>
          <span className="text-xs text-text-muted/60">{message.timestamp}</span>
        </div>

        {isUser ? (
          <div className="ml-auto max-w-[85%]">
            <div className={`${t.classes.userMsgBg} rounded-2xl rounded-tr-sm px-5 py-4 border ${t.classes.userMsgBorder} backdrop-blur-sm`}>
              <p className={`text-base leading-7 ${t.classes.userMsgText}`}>{message.content}</p>
            </div>
          </div>
        ) : (
          <div>
            {guardrailInfo?.triggered && (
              <GuardrailCard
                message={message.content}
                suggestedSubject={guardrailInfo.suggestedSubject}
                onSwitchSubject={onSwitchSubject}
              />
            )}

            {!guardrailInfo?.triggered && (
              <>
            {workflow && workflow.hasTools && (
              <AgenticWorkflow
                steps={workflow.steps || []}
                activeStep={workflow.activeStep}
                thinking={workflow.thinking}
                plan={workflow.plan}
                verification={workflow.verification}
                searchTrail={searchTrail}
                isComplete={workflow.isComplete}
                showDetails={false}
                theme={theme}
              />
            )}

            {searchTrail && !workflow?.hasTools && (
              <SearchTrailIndicator searchTrail={searchTrail} theme={theme} />
            )}

            {thinking && (
              isDarkTheme(subjectId) ? (
                <ThinkingDropdown thinking={thinking} isStreaming={isStreaming} />
              ) : (
                <ThinkingDropdownLight thinking={thinking} isStreaming={isStreaming} />
              )
            )}

            {clarification && (
              <ClarificationRequest
                reason={clarification.reason}
                suggestions={clarification.suggestions}
                searchTrail={clarification.searchTrail}
                onSuggestionClick={onSuggestionClick}
                theme={theme}
              />
            )}

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

            {linkPreviews && linkPreviews.length > 0 && (
              <div className="mt-4">
                <LinkPreviewGrid links={linkPreviews} theme={theme} />
              </div>
            )}

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
                          {String(children).replace(/
$/, '')}
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
                        Listen to {tutor?.name || 'Scoratis'}
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

            {(video || generatingVideo) && (
              <InlineVideoCard
                video={video}
                isGenerating={!!generatingVideo}
                progress={generatingVideo?.progress}
                stage={generatingVideo?.stage}
                topic={generatingVideo?.topic || video?.topic}
                onRemove={onRemoveVideo}
              />
            )}

            {showVideoOffer && videoRecommendation && !video && !generatingVideo && (
              <VideoOfferCard
                recommendation={videoRecommendation}
                onAccept={handleAcceptVideo}
                onDismiss={handleDismissVideo}
              />
            )}

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
                          <p className="text-sm font-medium text-text-primary truncate mb-1">
                            {source.document_title || 'Reference'}
                          </p>
                          <p className="text-xs text-text-muted line-clamp-1 italic">
                            "{source.content?.substring(0, 100)}..."
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
