import React from 'react';
import MessageCard from './MessageCard';
import TypingIndicator from './TypingIndicator';

export default function MessageList({
  messages,
  loading,
  currentSubject,
  theme,
  isDark,
  messagesEndRef,
  // Props to pass to MessageCard
  playingMessageId,
  loadingAudioIds,
  onPlayAudio,
  onPauseAudio,
  messageAudioUrls,
  messageVideos,
  generatingVideos,
  onRemoveVideo,
  videoRecommendations,
  onAcceptVideo,
  onDismissVideo,
  messageSources,
  messageWorkflows,
  guardrailMessages,
  onSwitchSubject,
  onCitationClick,
  messageSearchTrails,
  messageClarifications,
  messageAnimations,
  messageLinkPreviews,
  messageImages,
  messageThinking,
  streamingMessageId,
  streamingContent,
  onSuggestionClick
}) {
  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden relative scroll-smooth bg-bg-primary">
      <div className="flex flex-col min-h-full">
        <div className="flex-1">
          {messages.map((msg, idx) => (
            <MessageCard
              key={msg.id || idx}
              message={msg.id === streamingMessageId ? { ...msg, content: streamingContent } : msg}
              index={idx}
              audioUrl={messageAudioUrls[msg.id]}
              isCurrentlyPlaying={playingMessageId === msg.id}
              isLoadingAudio={loadingAudioIds.has(msg.id)}
              onPlayAudio={onPlayAudio}
              onPauseAudio={onPauseAudio}
              video={messageVideos[msg.id]}
              generatingVideo={generatingVideos[msg.id]}
              onRemoveVideo={() => onRemoveVideo(msg.id)}
              videoRecommendation={videoRecommendations[msg.id]}
              onAcceptVideo={onAcceptVideo}
              onDismissVideo={onDismissVideo}
              theme={theme}
              subjectId={currentSubject?.id}
              sources={messageSources[msg.id]}
              workflow={messageWorkflows[msg.id]}
              guardrailInfo={guardrailMessages[msg.id]}
              onSwitchSubject={onSwitchSubject}
              onCitationClick={onCitationClick}
              searchTrail={messageSearchTrails[msg.id]}
              clarification={messageClarifications[msg.id]}
              animations={messageAnimations[msg.id]}
              linkPreviews={messageLinkPreviews[msg.id]}
              images={messageImages[msg.id]}
              thinking={messageThinking[msg.id]}
              isStreaming={msg.id === streamingMessageId}
              onSuggestionClick={onSuggestionClick}
            />
          ))}

          {loading && (
            <TypingIndicator
              currentSubject={currentSubject}
              isDark={isDark}
            />
          )}
          <div ref={messagesEndRef} className="h-4 w-full" />
        </div>
      </div>
    </div>
  );
}
