/**
 * Subject-Specific Theme Configuration
 * Olive/Athenian base theme with subject-specific images, accents, and famous tutors
 */

// Base Athenian theme colors - Black text/icons with warm backgrounds
const ATHENIAN_BASE = {
  colors: {
    primary: '#1a1a1a',
    primaryDark: '#000000',
    primaryLight: '#333333',
    cream: '#F5F0E6',
    parchment: '#FAF6ED',
    sand: '#EBE5D8',
    border: '#D4CFB8',
    text: '#1a1a1a',
    textMuted: '#666666',
  },
  classes: {
    // Background - consistent warm Athenian theme
    pageBg: 'bg-gradient-to-br from-[#f5f0e6] via-[#faf6ed] to-[#ebe5d8]',

    // Header - dark gradient for contrast
    headerBg: 'bg-gradient-to-r from-[#2a2a2a] to-[#1a1a1a]',
    headerText: 'text-white',

    // Messages
    userMsgBg: 'bg-gray-100/80',
    userMsgBorder: 'border-gray-200',
    userMsgText: 'text-gray-900',
    aiMsgBg: 'bg-white/70',
    aiMsgAccent: 'text-gray-900',
    aiMsgBorder: 'border-gray-200',

    // Input
    inputBg: 'bg-white/90',
    inputBorder: 'border-gray-300',
    inputFocus: 'focus-within:border-gray-900 focus-within:ring-2 focus-within:ring-gray-200',
    sendBtn: 'bg-gray-900 hover:bg-black',

    // Sidebar
    sidebarBg: 'bg-[#faf6ed]/95',
    sidebarBorder: 'border-gray-200',
    activeItem: 'bg-gray-100 border-l-2 border-gray-900',

    // Accents - Black
    accent: 'text-gray-900',
    accentBg: 'bg-gray-900',
    accentHover: 'hover:bg-black',
    accentLight: 'bg-gray-100',
  }
};

export const SUBJECT_THEMES = {
  physics: {
    id: 'physics',
    name: 'Physics',
    icon: '⚛️',
    concept: 'Cosmic & Atomic',
    accentColor: '#3B82F6',

    // Famous tutor for this subject
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
      decoration: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#3B82F6' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  chemistry: {
    id: 'chemistry',
    name: 'Chemistry',
    icon: '🧪',
    concept: 'Molecular & Reactive',
    accentColor: '#10B981',

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
      decoration: 'https://images.unsplash.com/photo-1614935151651-0bea6508db6b?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#10B981' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  biology: {
    id: 'biology',
    name: 'Biology',
    icon: '🧬',
    concept: 'Organic & Living',
    accentColor: '#EC4899',

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
      decoration: 'https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#EC4899' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  mathematics: {
    id: 'mathematics',
    name: 'Mathematics',
    icon: '📐',
    concept: 'Geometric & Abstract',
    accentColor: '#8B5CF6',

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
      decoration: 'https://images.unsplash.com/photo-1453733190371-0a9bedd82893?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#8B5CF6' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  computer_science: {
    id: 'computer_science',
    name: 'Computer Science',
    icon: '💻',
    concept: 'Digital & Technical',
    accentColor: '#06B6D4',

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
      decoration: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#06B6D4' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  english: {
    id: 'english',
    name: 'English',
    icon: '📚',
    concept: 'Literary & Expressive',
    accentColor: '#F59E0B',

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
      decoration: 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#F59E0B' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  history: {
    id: 'history',
    name: 'History',
    icon: '🏛️',
    concept: 'Ancient & Classical',
    accentColor: '#78716C',

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
      decoration: 'https://images.unsplash.com/photo-1553913861-c0fddf2619ee?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#78716C' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  philosophy: {
    id: 'philosophy',
    name: 'Philosophy',
    icon: '🤔',
    concept: 'Contemplative & Wisdom',
    accentColor: '#6366F1',

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
      decoration: 'https://images.unsplash.com/photo-1490730141103-6cac27abb37f?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#6366F1' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  psychology: {
    id: 'psychology',
    name: 'Psychology',
    icon: '🧠',
    concept: 'Mind & Cognition',
    accentColor: '#F472B6',

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
      decoration: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#F472B6' },
    classes: { ...ATHENIAN_BASE.classes },
  },

  economics: {
    id: 'economics',
    name: 'Economics',
    icon: '📊',
    concept: 'Financial & Analytical',
    accentColor: '#22C55E',

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
      decoration: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&q=80',
    },

    colors: { ...ATHENIAN_BASE.colors, accent: '#22C55E' },
    classes: { ...ATHENIAN_BASE.classes },
  },
};

// Default theme (General/No subject) - Pure Athenian with Socrates
export const DEFAULT_THEME = {
  id: 'general',
  name: 'Scoratis',
  icon: '🏛️',
  concept: 'Athenian Wisdom',
  accentColor: '#6B7C5E',

  tutor: {
    name: 'Socrates',
    title: 'Classical Philosopher',
    years: '470-399 BC',
    quote: '"I know that I know nothing."',
    portrait: 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Socrate_du_Louvre.jpg/220px-Socrate_du_Louvre.jpg',
  },

  images: {
    header: 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=1200&q=80',
    welcome: 'https://images.unsplash.com/photo-1603565816030-6b389eeb23cb?w=800&q=80',
    avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Socrate_du_Louvre.jpg/220px-Socrate_du_Louvre.jpg',
    decoration: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80',
  },

  colors: ATHENIAN_BASE.colors,
  classes: ATHENIAN_BASE.classes,
};

/**
 * Get theme for a subject
 * @param {string} subjectId - The subject ID (e.g., 'physics', 'chemistry')
 * @returns {object} Theme configuration object
 */
export function getSubjectTheme(subjectId) {
  if (!subjectId || subjectId === 'general') {
    return DEFAULT_THEME;
  }
  return SUBJECT_THEMES[subjectId] || DEFAULT_THEME;
}

/**
 * Get theme class for a specific element
 * @param {string} subjectId - The subject ID
 * @param {string} element - The element name (e.g., 'pageBg', 'headerBg')
 * @returns {string} Tailwind class string
 */
export function getThemeClass(subjectId, element) {
  const theme = getSubjectTheme(subjectId);
  return theme.classes[element] || DEFAULT_THEME.classes[element] || '';
}

/**
 * Get theme color for CSS variables
 * @param {string} subjectId - The subject ID
 * @param {string} colorName - The color name (e.g., 'primary', 'background')
 * @returns {string} Hex color value
 */
export function getThemeColor(subjectId, colorName) {
  const theme = getSubjectTheme(subjectId);
  return theme.colors[colorName] || DEFAULT_THEME.colors[colorName] || '#6B7C5E';
}

/**
 * Get subject image URL
 * @param {string} subjectId - The subject ID
 * @param {string} imageType - The image type ('header', 'welcome', 'avatar', 'decoration')
 * @returns {string} Image URL
 */
export function getSubjectImage(subjectId, imageType) {
  const theme = getSubjectTheme(subjectId);
  return theme.images?.[imageType] || DEFAULT_THEME.images[imageType] || '';
}

/**
 * Get tutor info for a subject
 * @param {string} subjectId - The subject ID
 * @returns {object} Tutor info object with name, title, years, quote, portrait
 */
export function getSubjectTutor(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.tutor || DEFAULT_THEME.tutor;
}

export default SUBJECT_THEMES;
