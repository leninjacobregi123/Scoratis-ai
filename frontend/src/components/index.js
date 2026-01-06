/**
 * Component Index - Export all UI components
 * For easier importing across the application
 */

// Citation Components
export {
  CitationNumber,
  CitationPopup,
  CitationList,
  SourcesBadge,
  SuperscriptCitation,
  FootnotesSection,
  FormattedFootnotes,
  toSuperscript
} from './Citation';

// Search Trail Components
export {
  SearchTrailIndicator,
  SearchFallbackIndicator
} from './SearchTrailIndicator';

// Clarification Request
export { default as ClarificationRequest } from './ClarificationRequest';

// Manim Animation Card
export { default as ManimAnimationCard } from './ManimAnimationCard';

// Link Preview Components
export {
  LinkPreviewCard,
  LinkPreviewGrid,
  ExpandableLinkPreview
} from './LinkPreviewCard';

// Inline Image Components
export {
  InlineImage,
  ImageGallery,
  ImageThumbnail
} from './InlineImage';

// Agentic Workflow
export {
  default as AgenticWorkflow,
  useAgenticWorkflow
} from './AgenticWorkflow';

// Chat Components
export {
  AttachmentButton,
  AttachmentPreview,
  UploadProgressOverlay
} from './ChatAttachments';

export {
  ChatOptionsBar,
  DEFAULT_CHAT_OPTIONS
} from './ChatOptions';

export {
  CanvasPanel,
  CanvasToggleButton
} from './CanvasPanel';

// Background Components
export { default as SubjectBackground } from './SubjectBackground';

// LLM Switcher
export { default as LLMSwitcher } from './LLMSwitcher';
