/**
 * Subject-Specific Theme Configuration
 * All subjects use the standardized Athenian light theme
 * Each subject keeps its unique tutor personality
 */

// ============================================
// STANDARDIZED LIGHT THEME (Athenian)
// Used by all subjects for consistent UI
// ============================================
const STANDARD_LIGHT_THEME = {
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

  particles: null, // No particles for clean standardized look

  background: {
    gradient: 'radial-gradient(ellipse at top, #FFFFFF 0%, #FAF6ED 50%, #F5F0E6 100%)',
    overlay: 'none',
  },
};

// ============================================
// SUBJECT CONFIGURATIONS
// Each subject uses standardized theme + unique tutor
// ============================================

export const SUBJECT_THEMES = {
  // Physics - Albert Einstein
  physics: {
    id: 'physics',
    name: 'Physics',
    icon: '\u269B\uFE0F',
    concept: 'Science of Matter & Energy',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Albert Einstein',
      title: 'Theoretical Physicist',
      years: '1879-1955',
      quote: '"Imagination is more important than knowledge."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Albert_Einstein_1947.jpg/220px-Albert_Einstein_1947.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Albert_Einstein_1947.jpg/220px-Albert_Einstein_1947.jpg',
    },
  },

  // Chemistry - Marie Curie
  chemistry: {
    id: 'chemistry',
    name: 'Chemistry',
    icon: '\uD83E\uDDEA',
    concept: 'Science of Matter & Reactions',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Marie Curie',
      title: 'Chemist & Physicist',
      years: '1867-1934',
      quote: '"Nothing in life is to be feared, it is only to be understood."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Marie_Curie_c._1920s.jpg/220px-Marie_Curie_c._1920s.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1603126857599-f6e157fa2fe6?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Marie_Curie_c._1920s.jpg/220px-Marie_Curie_c._1920s.jpg',
    },
  },

  // Biology - Charles Darwin
  biology: {
    id: 'biology',
    name: 'Biology',
    icon: '\uD83E\uDDEC',
    concept: 'Science of Life',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Charles Darwin',
      title: 'Naturalist & Biologist',
      years: '1809-1882',
      quote: '"It is not the strongest that survives, but the most adaptable."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Charles_Darwin_seated_crop.jpg/220px-Charles_Darwin_seated_crop.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Charles_Darwin_seated_crop.jpg/220px-Charles_Darwin_seated_crop.jpg',
    },
  },

  // Mathematics - Pythagoras
  mathematics: {
    id: 'mathematics',
    name: 'Mathematics',
    icon: '\uD83D\uDCD0',
    concept: 'Science of Numbers & Patterns',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Pythagoras',
      title: 'Mathematician & Philosopher',
      years: '570-495 BC',
      quote: '"Number is the ruler of forms and ideas."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Kapitolinischer_Pythagoras_adjusted.jpg/220px-Kapitolinischer_Pythagoras_adjusted.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1509228468518-180dd4864904?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Kapitolinischer_Pythagoras_adjusted.jpg/220px-Kapitolinischer_Pythagoras_adjusted.jpg',
    },
  },

  // Computer Science - Alan Turing
  computer_science: {
    id: 'computer_science',
    name: 'Computer Science',
    icon: '\uD83D\uDCBB',
    concept: 'Science of Computing',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Alan Turing',
      title: 'Computer Scientist',
      years: '1912-1954',
      quote: '"We can only see a short distance ahead, but we can see plenty there that needs to be done."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Alan_Turing_Aged_16.jpg/220px-Alan_Turing_Aged_16.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Alan_Turing_Aged_16.jpg/220px-Alan_Turing_Aged_16.jpg',
    },
  },

  // English - William Shakespeare
  english: {
    id: 'english',
    name: 'English',
    icon: '\uD83D\uDCDA',
    concept: 'Language & Literature',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'William Shakespeare',
      title: 'Playwright & Poet',
      years: '1564-1616',
      quote: '"All the world\'s a stage, and all the men and women merely players."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Shakespeare.jpg/220px-Shakespeare.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Shakespeare.jpg/220px-Shakespeare.jpg',
    },
  },

  // History - Herodotus
  history: {
    id: 'history',
    name: 'History',
    icon: '\uD83C\uDFDB\uFE0F',
    concept: 'Study of the Past',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Herodotus',
      title: 'Father of History',
      years: '484-425 BC',
      quote: '"Great deeds are usually wrought at great risks."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Marble_bust_of_Herodotos_MET_DT11742.jpg/220px-Marble_bust_of_Herodotos_MET_DT11742.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1564399579883-451a5d44ec08?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1608326389682-02c0e6c94dfb?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Marble_bust_of_Herodotos_MET_DT11742.jpg/220px-Marble_bust_of_Herodotos_MET_DT11742.jpg',
    },
  },

  // Philosophy - Socrates
  philosophy: {
    id: 'philosophy',
    name: 'Philosophy',
    icon: '\uD83E\uDD14',
    concept: 'Love of Wisdom',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Socrates',
      title: 'Classical Philosopher',
      years: '470-399 BC',
      quote: '"The unexamined life is not worth living."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Socrate_du_Louvre.jpg/220px-Socrate_du_Louvre.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1544716278-e513176f20b5?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Socrate_du_Louvre.jpg/220px-Socrate_du_Louvre.jpg',
    },
  },

  // Psychology - Sigmund Freud
  psychology: {
    id: 'psychology',
    name: 'Psychology',
    icon: '\uD83E\uDDE0',
    concept: 'Study of the Mind',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Sigmund Freud',
      title: 'Father of Psychoanalysis',
      years: '1856-1939',
      quote: '"The mind is like an iceberg, it floats with one-seventh of its bulk above water."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Sigmund_Freud%2C_by_Max_Halberstadt_%28cropped%29.jpg/220px-Sigmund_Freud%2C_by_Max_Halberstadt_%28cropped%29.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Sigmund_Freud%2C_by_Max_Halberstadt_%28cropped%29.jpg/220px-Sigmund_Freud%2C_by_Max_Halberstadt_%28cropped%29.jpg',
    },
  },

  // Economics - Adam Smith
  economics: {
    id: 'economics',
    name: 'Economics',
    icon: '\uD83D\uDCCA',
    concept: 'Study of Wealth & Resources',
    ...STANDARD_LIGHT_THEME,
    tutor: {
      name: 'Adam Smith',
      title: 'Father of Economics',
      years: '1723-1790',
      quote: '"The real tragedy of the poor is the poverty of their aspirations."',
      portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/AdamSmith.jpg/220px-AdamSmith.jpg',
    },
    images: {
      header: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80',
      welcome: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80',
      avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/AdamSmith.jpg/220px-AdamSmith.jpg',
    },
  },
};

// ============================================
// DEFAULT THEME (General/No subject)
// ============================================
export const DEFAULT_THEME = {
  id: 'general',
  name: 'Scoratis',
  icon: '\uD83C\uDFDB\uFE0F',
  concept: 'Athenian Wisdom',
  ...STANDARD_LIGHT_THEME,
  tutor: {
    name: 'Socrates',
    title: 'Classical Philosopher',
    years: '470-399 BC',
    quote: '"I know that I know nothing."',
    // Bundled locally rather than hotlinked - external image hosts
    // (Wikimedia, Unsplash) are not reliable enough for core UI: they can
    // rate-limit, block hotlinking, or move/rename files without notice,
    // and this is the default tutor shown whenever no subject is selected.
    portrait: '/socrates-nobg.png',
  },
  images: {
    header: 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=1200&q=80',
    welcome: 'https://images.unsplash.com/photo-1603565816030-6b389eeb23cb?w=800&q=80',
    avatar: '/socrates-nobg.png',
  },
};

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Get theme for a subject
 */
export function getSubjectTheme(subjectId) {
  if (!subjectId || subjectId === 'general') {
    return DEFAULT_THEME;
  }
  return SUBJECT_THEMES[subjectId] || DEFAULT_THEME;
}

/**
 * Get theme class for a specific element
 */
export function getThemeClass(subjectId, element) {
  const theme = getSubjectTheme(subjectId);
  return theme.classes[element] || DEFAULT_THEME.classes[element] || '';
}

/**
 * Get theme color
 */
export function getThemeColor(subjectId, colorName) {
  const theme = getSubjectTheme(subjectId);
  return theme.colors[colorName] || DEFAULT_THEME.colors[colorName] || '#6b7c5e';
}

/**
 * Get subject image URL
 */
export function getSubjectImage(subjectId, imageType) {
  const theme = getSubjectTheme(subjectId);
  return theme.images?.[imageType] || DEFAULT_THEME.images[imageType] || '';
}

/**
 * Get tutor info for a subject
 */
export function getSubjectTutor(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.tutor || DEFAULT_THEME.tutor;
}

/**
 * Get particle configuration (now returns null for standardized theme)
 */
export function getParticleConfig(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.particles || null;
}

/**
 * Get background configuration
 */
export function getBackgroundConfig(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.background || DEFAULT_THEME.background;
}

/**
 * Check if theme is dark mode (always false for standardized theme)
 */
export function isDarkTheme(subjectId) {
  return false; // All subjects now use light theme
}

/**
 * Get standardized theme classes
 */
export function getStandardizedThemeClasses(subjectId) {
  const theme = getSubjectTheme(subjectId);
  const classes = theme.classes || {};

  return {
    ...classes,
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

export default SUBJECT_THEMES;
