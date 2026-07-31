/**
 * App theme configuration - Athenian light theme, Socrates persona.
 *
 * This used to be a per-subject lookup table (a different theme, tutor
 * portrait, and particle effect for each of 11 subjects). Scoratis is now
 * a single unified experience, so this collapsed to one static theme -
 * kept as a module (rather than inlined into every consumer) since several
 * pages still import THEME/TUTOR directly.
 */

export const THEME = {
  mood: 'light',
  era: 'athenian-classical',

  colors: {
    primary: '#6b7c5e',
    primaryDark: '#4a5a40',
    primaryLight: '#8a9a7a',
    bgPrimary: '#F5F0E6',
    bgSecondary: '#FAF6ED',
    bgTertiary: '#EBE5D8',
    textPrimary: '#4a5a40',
    textSecondary: '#6b7c5e',
    textMuted: '#8a8a7a',
    accent: '#6b7c5e',
    accentLight: '#8a9a7a',
    accentDark: '#4a5a40',
    border: '#D4CFB8',
    borderLight: '#E7E5E4',
  },

  classes: {
    pageBg: 'bg-gradient-to-br from-[#F5F0E6] via-[#FAF6ED] to-[#EBE5D8]',
    headerBg: 'bg-gradient-to-r from-[#4a5a40]/95 to-[#3a4a30]/95',
    headerText: 'text-white',
    headerOverlay: 'from-[#4a5a40]/30 via-[#3a4a30]/50 to-[#2a3a20]/60',
    userMsgBg: 'bg-[#6b7c5e]/10',
    userMsgBorder: 'border-[#6b7c5e]/30',
    userMsgText: 'text-[#4a5a40]',
    aiMsgBg: 'bg-white/70',
    aiMsgAccent: 'text-[#6b7c5e]',
    aiMsgBorder: 'border-gray-200',
    inputBg: 'bg-white/90',
    inputBorder: 'border-gray-300',
    inputFocus: 'focus-within:border-[#6b7c5e] focus-within:ring-2 focus-within:ring-[#6b7c5e]/20',
    inputText: 'text-gray-900',
    inputPlaceholder: 'placeholder-gray-400',
    sendBtn: 'bg-[#6b7c5e] hover:bg-[#5a6c4e] text-white',
    sidebarBg: 'bg-[#faf6ed]/95',
    sidebarBorder: 'border-gray-200',
    sidebarText: 'text-gray-900',
    sidebarTextMuted: 'text-gray-500',
    activeItem: 'bg-[#6b7c5e]/10 border-l-2 border-[#6b7c5e]',
    hoverItem: 'hover:bg-gray-100',
    accent: 'text-[#6b7c5e]',
    accentBg: 'bg-[#6b7c5e]',
    accentHover: 'hover:bg-[#5a6c4e]',
    accentLight: 'bg-[#6b7c5e]/10',
    codeBlockBg: 'bg-gray-50',
    blockquoteBorder: 'border-l-4 border-[#6b7c5e]',
    scrollbarTrack: 'scrollbar-track-gray-100',
    scrollbarThumb: 'scrollbar-thumb-[#6b7c5e]',
    welcomeBg: 'bg-white/80',
    welcomeBorder: 'border-gray-200',
    optionPillBg: 'bg-white/80',
    optionPillBorder: 'border-gray-300',
    optionPillActive: 'bg-[#6b7c5e]/10 border-[#6b7c5e]',
  },

  background: {
    gradient: 'radial-gradient(ellipse at top, #FFFFFF 0%, #FAF6ED 50%, #F5F0E6 100%)',
    overlay: 'none',
  },
};

export const TUTOR = {
  name: 'Socrates',
  title: 'Classical Philosopher',
  years: '470-399 BC',
  quote: '"I know that I know nothing."',
  // Bundled locally rather than hotlinked - external image hosts (Wikimedia,
  // Unsplash) are not reliable enough for core UI: they can rate-limit,
  // block hotlinking, or move/rename files without notice.
  portrait: '/socrates-nobg.png',
};

export const THEME_IMAGES = {
  header: 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=1200&q=80',
  welcome: 'https://images.unsplash.com/photo-1603565816030-6b389eeb23cb?w=800&q=80',
  avatar: '/socrates-nobg.png',
};

/**
 * Flattened classes object some older call sites expect, with a few
 * generic overrides layered on top (kept from the original standardized
 * theme so existing components render identically).
 */
export function getStandardizedThemeClasses() {
  return {
    ...THEME.classes,
    bgPrimary: 'bg-[#6b7c5e]',
    bgSecondary: 'bg-gray-50',
    bgTertiary: 'bg-gray-100',
    text: 'text-gray-700',
    textPrimary: 'text-[#6b7c5e]',
    textMuted: 'text-gray-500',
    textOnPrimary: 'text-white',
    border: 'border-gray-200',
    borderLight: 'border-gray-300',
    searchTrailBg: 'bg-gray-50',
    searchResultSuccess: 'bg-green-100 text-green-700',
    searchResultEmpty: 'bg-amber-100 text-amber-700',
    clarificationBg: 'bg-amber-50',
    clarificationBorder: 'border-amber-300',
    clarificationText: 'text-amber-900',
    animationCardBg: 'bg-white',
    linkPreviewBg: 'bg-white',
    imageBg: 'bg-gray-50',
  };
}
