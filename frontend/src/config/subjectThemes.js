/**
 * Subject-Specific Theme Configuration
 * Era-Authentic Persona Realms - Each subject has its own immersive visual identity
 */

// ============================================
// COMPLETE THEME CONFIGURATIONS PER SUBJECT
// ============================================

export const SUBJECT_THEMES = {
  // ==========================================
  // PHYSICS - Albert Einstein (Cosmic/Space)
  // Era: Early 20th Century / Cosmic
  // ==========================================
  physics: {
    id: 'physics',
    name: 'Physics',
    icon: '⚛️',
    concept: 'Cosmic & Atomic',
    era: 'cosmic-modern',
    mood: 'dark',

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

    colors: {
      primary: '#3B82F6',
      primaryDark: '#1E40AF',
      primaryLight: '#60A5FA',
      bgPrimary: '#0F172A',
      bgSecondary: '#1E293B',
      bgTertiary: '#334155',
      textPrimary: '#F1F5F9',
      textSecondary: '#94A3B8',
      textMuted: '#64748B',
      accent: '#3B82F6',
      accentLight: '#60A5FA',
      accentDark: '#1D4ED8',
      border: '#334155',
      borderLight: '#475569',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A]',
      headerBg: 'bg-gradient-to-r from-[#1E293B]/95 to-[#0F172A]/95',
      headerText: 'text-white',
      headerOverlay: 'from-blue-900/40 via-slate-900/60 to-slate-900/80',
      userMsgBg: 'bg-blue-900/40',
      userMsgBorder: 'border-blue-700/50',
      userMsgText: 'text-blue-100',
      aiMsgBg: 'bg-slate-800/60',
      aiMsgAccent: 'text-blue-300',
      aiMsgBorder: 'border-slate-600/30',
      inputBg: 'bg-slate-800/80',
      inputBorder: 'border-slate-600',
      inputFocus: 'focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20',
      inputText: 'text-slate-100',
      inputPlaceholder: 'placeholder-slate-400',
      sendBtn: 'bg-blue-600 hover:bg-blue-500 text-white',
      sidebarBg: 'bg-slate-900/95',
      sidebarBorder: 'border-slate-700',
      sidebarText: 'text-slate-200',
      sidebarTextMuted: 'text-slate-400',
      activeItem: 'bg-blue-900/50 border-l-2 border-blue-500',
      hoverItem: 'hover:bg-slate-800',
      accent: 'text-blue-400',
      accentBg: 'bg-blue-600',
      accentHover: 'hover:bg-blue-500',
      accentLight: 'bg-blue-900/30',
      codeBlockBg: 'bg-slate-900',
      blockquoteBorder: 'border-l-4 border-blue-500',
      scrollbarTrack: 'scrollbar-track-slate-800',
      scrollbarThumb: 'scrollbar-thumb-blue-600',
      welcomeBg: 'bg-slate-900/80',
      welcomeBorder: 'border-slate-700',
      optionPillBg: 'bg-slate-800/80',
      optionPillBorder: 'border-slate-600',
      optionPillActive: 'bg-blue-600/30 border-blue-500',
    },

    particles: {
      type: 'stars',
      count: 60,
      colors: ['#3B82F6', '#60A5FA', '#93C5FD', '#FFFFFF'],
      speed: 'slow',
      opacity: 0.7,
    },

    background: {
      gradient: 'radial-gradient(ellipse at top, #1E40AF 0%, #0F172A 50%, #000000 100%)',
      overlay: 'cosmic-dust',
    },

  },

  // ==========================================
  // CHEMISTRY - Marie Curie (Laboratory/Molecular)
  // Era: Victorian Laboratory
  // ==========================================
  chemistry: {
    id: 'chemistry',
    name: 'Chemistry',
    icon: '🧪',
    concept: 'Molecular & Reactive',
    era: 'laboratory-victorian',
    mood: 'cool',

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

    colors: {
      primary: '#10B981',
      primaryDark: '#059669',
      primaryLight: '#34D399',
      bgPrimary: '#022C22',
      bgSecondary: '#064E3B',
      bgTertiary: '#065F46',
      textPrimary: '#D1FAE5',
      textSecondary: '#A7F3D0',
      textMuted: '#6EE7B7',
      accent: '#10B981',
      accentLight: '#34D399',
      accentDark: '#059669',
      border: '#065F46',
      borderLight: '#047857',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#022C22] via-[#064E3B] to-[#022C22]',
      headerBg: 'bg-gradient-to-r from-[#064E3B]/95 to-[#022C22]/95',
      headerText: 'text-white',
      headerOverlay: 'from-emerald-900/40 via-teal-900/60 to-emerald-950/80',
      userMsgBg: 'bg-emerald-900/40',
      userMsgBorder: 'border-emerald-700/50',
      userMsgText: 'text-emerald-100',
      aiMsgBg: 'bg-teal-900/50',
      aiMsgAccent: 'text-emerald-300',
      aiMsgBorder: 'border-teal-700/30',
      inputBg: 'bg-emerald-950/80',
      inputBorder: 'border-emerald-700',
      inputFocus: 'focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20',
      inputText: 'text-emerald-100',
      inputPlaceholder: 'placeholder-emerald-400',
      sendBtn: 'bg-emerald-600 hover:bg-emerald-500 text-white',
      sidebarBg: 'bg-emerald-950/95',
      sidebarBorder: 'border-emerald-800',
      sidebarText: 'text-emerald-100',
      sidebarTextMuted: 'text-emerald-400',
      activeItem: 'bg-emerald-900/50 border-l-2 border-emerald-500',
      hoverItem: 'hover:bg-emerald-900/40',
      accent: 'text-emerald-400',
      accentBg: 'bg-emerald-600',
      accentHover: 'hover:bg-emerald-500',
      accentLight: 'bg-emerald-900/30',
      codeBlockBg: 'bg-emerald-950',
      blockquoteBorder: 'border-l-4 border-emerald-500',
      scrollbarTrack: 'scrollbar-track-emerald-950',
      scrollbarThumb: 'scrollbar-thumb-emerald-600',
      welcomeBg: 'bg-emerald-950/80',
      welcomeBorder: 'border-emerald-800',
      optionPillBg: 'bg-emerald-900/80',
      optionPillBorder: 'border-emerald-700',
      optionPillActive: 'bg-emerald-600/30 border-emerald-500',
    },

    particles: {
      type: 'bubbles',
      count: 35,
      colors: ['#10B981', '#34D399', '#6EE7B7', '#A7F3D0'],
      speed: 'medium',
      opacity: 0.6,
    },

    background: {
      gradient: 'radial-gradient(ellipse at bottom, #065F46 0%, #022C22 60%, #011815 100%)',
      overlay: 'molecular',
    },

  },

  // ==========================================
  // BIOLOGY - Charles Darwin (Nature/Organic)
  // Era: Victorian Naturalist
  // ==========================================
  biology: {
    id: 'biology',
    name: 'Biology',
    icon: '🧬',
    concept: 'Organic & Living',
    era: 'victorian-naturalist',
    mood: 'warm',

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

    colors: {
      primary: '#EC4899',
      primaryDark: '#DB2777',
      primaryLight: '#F472B6',
      bgPrimary: '#1A0F14',
      bgSecondary: '#2D1F26',
      bgTertiary: '#3D2A33',
      textPrimary: '#FDF2F8',
      textSecondary: '#FBCFE8',
      textMuted: '#F9A8D4',
      accent: '#EC4899',
      accentLight: '#F472B6',
      accentDark: '#DB2777',
      border: '#3D2A33',
      borderLight: '#4A3340',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#1A0F14] via-[#2D1F26] to-[#14532D]/30',
      headerBg: 'bg-gradient-to-r from-[#2D1F26]/95 to-[#1A0F14]/95',
      headerText: 'text-white',
      headerOverlay: 'from-pink-900/40 via-rose-900/50 to-stone-900/70',
      userMsgBg: 'bg-pink-900/40',
      userMsgBorder: 'border-pink-700/50',
      userMsgText: 'text-pink-100',
      aiMsgBg: 'bg-stone-800/60',
      aiMsgAccent: 'text-pink-300',
      aiMsgBorder: 'border-stone-600/30',
      inputBg: 'bg-stone-900/80',
      inputBorder: 'border-pink-800/50',
      inputFocus: 'focus-within:border-pink-500 focus-within:ring-2 focus-within:ring-pink-500/20',
      inputText: 'text-pink-100',
      inputPlaceholder: 'placeholder-pink-300/50',
      sendBtn: 'bg-pink-600 hover:bg-pink-500 text-white',
      sidebarBg: 'bg-stone-900/95',
      sidebarBorder: 'border-pink-900/50',
      sidebarText: 'text-pink-100',
      sidebarTextMuted: 'text-pink-300/60',
      activeItem: 'bg-pink-900/50 border-l-2 border-pink-500',
      hoverItem: 'hover:bg-stone-800',
      accent: 'text-pink-400',
      accentBg: 'bg-pink-600',
      accentHover: 'hover:bg-pink-500',
      accentLight: 'bg-pink-900/30',
      codeBlockBg: 'bg-stone-950',
      blockquoteBorder: 'border-l-4 border-pink-500',
      scrollbarTrack: 'scrollbar-track-stone-900',
      scrollbarThumb: 'scrollbar-thumb-pink-600',
      welcomeBg: 'bg-stone-900/80',
      welcomeBorder: 'border-pink-800/50',
      optionPillBg: 'bg-stone-800/80',
      optionPillBorder: 'border-pink-700/50',
      optionPillActive: 'bg-pink-600/30 border-pink-500',
    },

    particles: {
      type: 'cells',
      count: 30,
      colors: ['#EC4899', '#F472B6', '#34D399', '#4ADE80'],
      speed: 'slow',
      opacity: 0.5,
    },

    background: {
      gradient: 'radial-gradient(ellipse at center, #2D1F26 0%, #1A0F14 50%, #0F0A0C 100%)',
      overlay: 'organic',
    },

  },

  // ==========================================
  // MATHEMATICS - Pythagoras (Geometric/Ancient Greek)
  // Era: Ancient Greece
  // ==========================================
  mathematics: {
    id: 'mathematics',
    name: 'Mathematics',
    icon: '📐',
    concept: 'Geometric & Abstract',
    era: 'ancient-greek',
    mood: 'cool',

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

    colors: {
      primary: '#8B5CF6',
      primaryDark: '#7C3AED',
      primaryLight: '#A78BFA',
      bgPrimary: '#0C0A1D',
      bgSecondary: '#1E1B4B',
      bgTertiary: '#312E81',
      textPrimary: '#EDE9FE',
      textSecondary: '#DDD6FE',
      textMuted: '#C4B5FD',
      accent: '#8B5CF6',
      accentLight: '#A78BFA',
      accentDark: '#7C3AED',
      border: '#312E81',
      borderLight: '#4338CA',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#0C0A1D] via-[#1E1B4B] to-[#312E81]/50',
      headerBg: 'bg-gradient-to-r from-[#1E1B4B]/95 to-[#0C0A1D]/95',
      headerText: 'text-white',
      headerOverlay: 'from-violet-900/40 via-purple-900/50 to-indigo-950/70',
      userMsgBg: 'bg-violet-900/40',
      userMsgBorder: 'border-violet-700/50',
      userMsgText: 'text-violet-100',
      aiMsgBg: 'bg-indigo-950/60',
      aiMsgAccent: 'text-violet-300',
      aiMsgBorder: 'border-indigo-700/30',
      inputBg: 'bg-indigo-950/80',
      inputBorder: 'border-violet-700',
      inputFocus: 'focus-within:border-violet-500 focus-within:ring-2 focus-within:ring-violet-500/20',
      inputText: 'text-violet-100',
      inputPlaceholder: 'placeholder-violet-400',
      sendBtn: 'bg-violet-600 hover:bg-violet-500 text-white',
      sidebarBg: 'bg-indigo-950/95',
      sidebarBorder: 'border-violet-800',
      sidebarText: 'text-violet-100',
      sidebarTextMuted: 'text-violet-400',
      activeItem: 'bg-violet-900/50 border-l-2 border-violet-500',
      hoverItem: 'hover:bg-indigo-900/40',
      accent: 'text-violet-400',
      accentBg: 'bg-violet-600',
      accentHover: 'hover:bg-violet-500',
      accentLight: 'bg-violet-900/30',
      codeBlockBg: 'bg-indigo-950',
      blockquoteBorder: 'border-l-4 border-violet-500',
      scrollbarTrack: 'scrollbar-track-indigo-950',
      scrollbarThumb: 'scrollbar-thumb-violet-600',
      welcomeBg: 'bg-indigo-950/80',
      welcomeBorder: 'border-violet-800',
      optionPillBg: 'bg-indigo-900/80',
      optionPillBorder: 'border-violet-700',
      optionPillActive: 'bg-violet-600/30 border-violet-500',
    },

    particles: {
      type: 'shapes',
      count: 25,
      colors: ['#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE'],
      speed: 'slow',
      opacity: 0.5,
    },

    background: {
      gradient: 'radial-gradient(ellipse at top left, #4338CA 0%, #1E1B4B 40%, #0C0A1D 100%)',
      overlay: 'geometric',
    },

  },

  // ==========================================
  // COMPUTER SCIENCE - Alan Turing (Digital/Matrix)
  // Era: WWII Digital / Computing Pioneer
  // ==========================================
  computer_science: {
    id: 'computer_science',
    name: 'Computer Science',
    icon: '💻',
    concept: 'Digital & Technical',
    era: 'digital-wartime',
    mood: 'dark',

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

    colors: {
      primary: '#06B6D4',
      primaryDark: '#0891B2',
      primaryLight: '#22D3EE',
      bgPrimary: '#042F2E',
      bgSecondary: '#134E4A',
      bgTertiary: '#115E59',
      textPrimary: '#CCFBF1',
      textSecondary: '#99F6E4',
      textMuted: '#5EEAD4',
      accent: '#06B6D4',
      accentLight: '#22D3EE',
      accentDark: '#0891B2',
      border: '#115E59',
      borderLight: '#0D9488',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#042F2E] via-[#0F172A] to-[#042F2E]',
      headerBg: 'bg-gradient-to-r from-[#134E4A]/95 to-[#042F2E]/95',
      headerText: 'text-white',
      headerOverlay: 'from-cyan-900/40 via-teal-900/50 to-slate-900/70',
      userMsgBg: 'bg-cyan-900/40',
      userMsgBorder: 'border-cyan-700/50',
      userMsgText: 'text-cyan-100',
      aiMsgBg: 'bg-slate-900/70',
      aiMsgAccent: 'text-cyan-300',
      aiMsgBorder: 'border-teal-700/30',
      inputBg: 'bg-slate-900/80',
      inputBorder: 'border-cyan-700',
      inputFocus: 'focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-500/20',
      inputText: 'text-cyan-100',
      inputPlaceholder: 'placeholder-cyan-400',
      sendBtn: 'bg-cyan-600 hover:bg-cyan-500 text-white',
      sidebarBg: 'bg-slate-950/95',
      sidebarBorder: 'border-cyan-800',
      sidebarText: 'text-cyan-100',
      sidebarTextMuted: 'text-cyan-400',
      activeItem: 'bg-cyan-900/50 border-l-2 border-cyan-500',
      hoverItem: 'hover:bg-slate-900',
      accent: 'text-cyan-400',
      accentBg: 'bg-cyan-600',
      accentHover: 'hover:bg-cyan-500',
      accentLight: 'bg-cyan-900/30',
      codeBlockBg: 'bg-slate-950',
      blockquoteBorder: 'border-l-4 border-cyan-500',
      scrollbarTrack: 'scrollbar-track-slate-950',
      scrollbarThumb: 'scrollbar-thumb-cyan-600',
      welcomeBg: 'bg-slate-950/80',
      welcomeBorder: 'border-cyan-800',
      optionPillBg: 'bg-slate-900/80',
      optionPillBorder: 'border-cyan-700',
      optionPillActive: 'bg-cyan-600/30 border-cyan-500',
    },

    particles: {
      type: 'binary',
      count: 50,
      colors: ['#06B6D4', '#22D3EE', '#67E8F9', '#A5F3FC'],
      speed: 'fast',
      opacity: 0.6,
    },

    background: {
      gradient: 'linear-gradient(180deg, #042F2E 0%, #0F172A 50%, #020617 100%)',
      overlay: 'digital',
    },

  },

  // ==========================================
  // ENGLISH - William Shakespeare (Theatrical/Parchment)
  // Era: Elizabethan Theatre
  // ==========================================
  english: {
    id: 'english',
    name: 'English',
    icon: '📚',
    concept: 'Literary & Expressive',
    era: 'elizabethan-theatrical',
    mood: 'warm',

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

    colors: {
      primary: '#F59E0B',
      primaryDark: '#D97706',
      primaryLight: '#FBBF24',
      bgPrimary: '#1C1917',
      bgSecondary: '#292524',
      bgTertiary: '#44403C',
      textPrimary: '#FEFCE8',
      textSecondary: '#FEF3C7',
      textMuted: '#FDE68A',
      accent: '#F59E0B',
      accentLight: '#FBBF24',
      accentDark: '#D97706',
      border: '#44403C',
      borderLight: '#57534E',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#1C1917] via-[#292524] to-[#44403C]/50',
      headerBg: 'bg-gradient-to-r from-[#292524]/95 to-[#1C1917]/95',
      headerText: 'text-white',
      headerOverlay: 'from-amber-900/40 via-orange-900/50 to-stone-900/70',
      userMsgBg: 'bg-amber-900/40',
      userMsgBorder: 'border-amber-700/50',
      userMsgText: 'text-amber-100',
      aiMsgBg: 'bg-stone-800/70',
      aiMsgAccent: 'text-amber-300',
      aiMsgBorder: 'border-stone-600/30',
      inputBg: 'bg-stone-800/80',
      inputBorder: 'border-amber-700/50',
      inputFocus: 'focus-within:border-amber-500 focus-within:ring-2 focus-within:ring-amber-500/20',
      inputText: 'text-amber-100',
      inputPlaceholder: 'placeholder-amber-300/50',
      sendBtn: 'bg-amber-600 hover:bg-amber-500 text-white',
      sidebarBg: 'bg-stone-900/95',
      sidebarBorder: 'border-amber-800/50',
      sidebarText: 'text-amber-100',
      sidebarTextMuted: 'text-amber-300/60',
      activeItem: 'bg-amber-900/50 border-l-2 border-amber-500',
      hoverItem: 'hover:bg-stone-800',
      accent: 'text-amber-400',
      accentBg: 'bg-amber-600',
      accentHover: 'hover:bg-amber-500',
      accentLight: 'bg-amber-900/30',
      codeBlockBg: 'bg-stone-950',
      blockquoteBorder: 'border-l-4 border-amber-500',
      scrollbarTrack: 'scrollbar-track-stone-900',
      scrollbarThumb: 'scrollbar-thumb-amber-600',
      welcomeBg: 'bg-stone-900/80',
      welcomeBorder: 'border-amber-800/50',
      optionPillBg: 'bg-stone-800/80',
      optionPillBorder: 'border-amber-700/50',
      optionPillActive: 'bg-amber-600/30 border-amber-500',
    },

    particles: {
      type: 'quills',
      count: 20,
      colors: ['#F59E0B', '#FBBF24', '#FDE68A', '#FEF3C7'],
      speed: 'slow',
      opacity: 0.5,
    },

    background: {
      gradient: 'radial-gradient(ellipse at bottom right, #44403C 0%, #292524 40%, #1C1917 100%)',
      overlay: 'parchment',
    },

  },

  // ==========================================
  // HISTORY - Herodotus (Ancient/Classical)
  // Era: Ancient Classical
  // ==========================================
  history: {
    id: 'history',
    name: 'History',
    icon: '🏛️',
    concept: 'Ancient & Classical',
    era: 'ancient-classical',
    mood: 'warm',

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

    colors: {
      primary: '#78716C',
      primaryDark: '#57534E',
      primaryLight: '#A8A29E',
      bgPrimary: '#1C1917',
      bgSecondary: '#292524',
      bgTertiary: '#44403C',
      textPrimary: '#F5F5F4',
      textSecondary: '#E7E5E4',
      textMuted: '#D6D3D1',
      accent: '#78716C',
      accentLight: '#A8A29E',
      accentDark: '#57534E',
      border: '#44403C',
      borderLight: '#57534E',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#1C1917] via-[#292524] to-[#44403C]/30',
      headerBg: 'bg-gradient-to-r from-[#292524]/95 to-[#1C1917]/95',
      headerText: 'text-white',
      headerOverlay: 'from-stone-700/40 via-stone-800/50 to-stone-900/70',
      userMsgBg: 'bg-stone-700/50',
      userMsgBorder: 'border-stone-600/50',
      userMsgText: 'text-stone-100',
      aiMsgBg: 'bg-stone-800/60',
      aiMsgAccent: 'text-stone-300',
      aiMsgBorder: 'border-stone-600/30',
      inputBg: 'bg-stone-800/80',
      inputBorder: 'border-stone-600',
      inputFocus: 'focus-within:border-stone-500 focus-within:ring-2 focus-within:ring-stone-500/20',
      inputText: 'text-stone-100',
      inputPlaceholder: 'placeholder-stone-400',
      sendBtn: 'bg-stone-600 hover:bg-stone-500 text-white',
      sidebarBg: 'bg-stone-900/95',
      sidebarBorder: 'border-stone-700',
      sidebarText: 'text-stone-100',
      sidebarTextMuted: 'text-stone-400',
      activeItem: 'bg-stone-700/50 border-l-2 border-stone-500',
      hoverItem: 'hover:bg-stone-800',
      accent: 'text-stone-400',
      accentBg: 'bg-stone-600',
      accentHover: 'hover:bg-stone-500',
      accentLight: 'bg-stone-700/30',
      codeBlockBg: 'bg-stone-950',
      blockquoteBorder: 'border-l-4 border-stone-500',
      scrollbarTrack: 'scrollbar-track-stone-900',
      scrollbarThumb: 'scrollbar-thumb-stone-600',
      welcomeBg: 'bg-stone-900/80',
      welcomeBorder: 'border-stone-700',
      optionPillBg: 'bg-stone-800/80',
      optionPillBorder: 'border-stone-600',
      optionPillActive: 'bg-stone-600/30 border-stone-500',
    },

    particles: {
      type: 'dust',
      count: 40,
      colors: ['#78716C', '#A8A29E', '#D6D3D1', '#E7E5E4'],
      speed: 'slow',
      opacity: 0.4,
    },

    background: {
      gradient: 'radial-gradient(ellipse at center, #44403C 0%, #292524 50%, #1C1917 100%)',
      overlay: 'ancient',
    },

  },

  // ==========================================
  // PHILOSOPHY - Socrates (Athenian/Marble)
  // Era: Classical Athens (LIGHT THEME)
  // ==========================================
  philosophy: {
    id: 'philosophy',
    name: 'Philosophy',
    icon: '🤔',
    concept: 'Contemplative & Wisdom',
    era: 'athenian-classical',
    mood: 'light',

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

    colors: {
      primary: '#6366F1',
      primaryDark: '#4F46E5',
      primaryLight: '#818CF8',
      bgPrimary: '#F5F0E6',
      bgSecondary: '#FAF6ED',
      bgTertiary: '#EBE5D8',
      textPrimary: '#1E1B4B',
      textSecondary: '#312E81',
      textMuted: '#4338CA',
      accent: '#6366F1',
      accentLight: '#818CF8',
      accentDark: '#4F46E5',
      border: '#D4CFB8',
      borderLight: '#E7E5E4',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#F5F0E6] via-[#FAF6ED] to-[#EBE5D8]',
      headerBg: 'bg-gradient-to-r from-[#2a2a2a]/95 to-[#1a1a1a]/95',
      headerText: 'text-white',
      headerOverlay: 'from-indigo-900/30 via-slate-900/50 to-slate-900/60',
      userMsgBg: 'bg-indigo-100/60',
      userMsgBorder: 'border-indigo-200',
      userMsgText: 'text-indigo-900',
      aiMsgBg: 'bg-white/70',
      aiMsgAccent: 'text-indigo-700',
      aiMsgBorder: 'border-gray-200',
      inputBg: 'bg-white/90',
      inputBorder: 'border-gray-300',
      inputFocus: 'focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-200',
      inputText: 'text-gray-900',
      inputPlaceholder: 'placeholder-gray-400',
      sendBtn: 'bg-indigo-600 hover:bg-indigo-500 text-white',
      sidebarBg: 'bg-[#faf6ed]/95',
      sidebarBorder: 'border-gray-200',
      sidebarText: 'text-gray-900',
      sidebarTextMuted: 'text-gray-500',
      activeItem: 'bg-indigo-100 border-l-2 border-indigo-600',
      hoverItem: 'hover:bg-gray-100',
      accent: 'text-indigo-600',
      accentBg: 'bg-indigo-600',
      accentHover: 'hover:bg-indigo-500',
      accentLight: 'bg-indigo-100',
      codeBlockBg: 'bg-gray-50',
      blockquoteBorder: 'border-l-4 border-indigo-500',
      scrollbarTrack: 'scrollbar-track-gray-100',
      scrollbarThumb: 'scrollbar-thumb-indigo-400',
      welcomeBg: 'bg-white/80',
      welcomeBorder: 'border-gray-200',
      optionPillBg: 'bg-white/80',
      optionPillBorder: 'border-gray-300',
      optionPillActive: 'bg-indigo-100 border-indigo-500',
    },

    particles: {
      type: 'rays',
      count: 15,
      colors: ['#6366F1', '#818CF8', '#A5B4FC', '#C7D2FE'],
      speed: 'slow',
      opacity: 0.3,
    },

    background: {
      gradient: 'radial-gradient(ellipse at top, #FFFFFF 0%, #FAF6ED 50%, #F5F0E6 100%)',
      overlay: 'marble',
    },

  },

  // ==========================================
  // PSYCHOLOGY - Sigmund Freud (Victorian/Mind)
  // Era: Victorian Analytical
  // ==========================================
  psychology: {
    id: 'psychology',
    name: 'Psychology',
    icon: '🧠',
    concept: 'Mind & Cognition',
    era: 'victorian-analytical',
    mood: 'dark',

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

    colors: {
      primary: '#F472B6',
      primaryDark: '#EC4899',
      primaryLight: '#F9A8D4',
      bgPrimary: '#18181B',
      bgSecondary: '#27272A',
      bgTertiary: '#3F3F46',
      textPrimary: '#FCE7F3',
      textSecondary: '#FBCFE8',
      textMuted: '#F9A8D4',
      accent: '#F472B6',
      accentLight: '#F9A8D4',
      accentDark: '#EC4899',
      border: '#3F3F46',
      borderLight: '#52525B',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#18181B] via-[#27272A] to-[#3F3F46]/50',
      headerBg: 'bg-gradient-to-r from-[#27272A]/95 to-[#18181B]/95',
      headerText: 'text-white',
      headerOverlay: 'from-pink-900/40 via-fuchsia-900/50 to-zinc-900/70',
      userMsgBg: 'bg-pink-900/40',
      userMsgBorder: 'border-pink-700/50',
      userMsgText: 'text-pink-100',
      aiMsgBg: 'bg-zinc-800/60',
      aiMsgAccent: 'text-pink-300',
      aiMsgBorder: 'border-zinc-600/30',
      inputBg: 'bg-zinc-800/80',
      inputBorder: 'border-pink-700/50',
      inputFocus: 'focus-within:border-pink-500 focus-within:ring-2 focus-within:ring-pink-500/20',
      inputText: 'text-pink-100',
      inputPlaceholder: 'placeholder-pink-300/50',
      sendBtn: 'bg-pink-500 hover:bg-pink-400 text-white',
      sidebarBg: 'bg-zinc-900/95',
      sidebarBorder: 'border-pink-800/50',
      sidebarText: 'text-pink-100',
      sidebarTextMuted: 'text-pink-300/60',
      activeItem: 'bg-pink-900/50 border-l-2 border-pink-500',
      hoverItem: 'hover:bg-zinc-800',
      accent: 'text-pink-400',
      accentBg: 'bg-pink-500',
      accentHover: 'hover:bg-pink-400',
      accentLight: 'bg-pink-900/30',
      codeBlockBg: 'bg-zinc-950',
      blockquoteBorder: 'border-l-4 border-pink-500',
      scrollbarTrack: 'scrollbar-track-zinc-900',
      scrollbarThumb: 'scrollbar-thumb-pink-500',
      welcomeBg: 'bg-zinc-900/80',
      welcomeBorder: 'border-pink-800/50',
      optionPillBg: 'bg-zinc-800/80',
      optionPillBorder: 'border-pink-700/50',
      optionPillActive: 'bg-pink-600/30 border-pink-500',
    },

    particles: {
      type: 'neurons',
      count: 30,
      colors: ['#F472B6', '#F9A8D4', '#FBCFE8', '#FCE7F3'],
      speed: 'slow',
      opacity: 0.5,
    },

    background: {
      gradient: 'radial-gradient(ellipse at center, #3F3F46 0%, #27272A 50%, #18181B 100%)',
      overlay: 'mind',
    },

  },

  // ==========================================
  // ECONOMICS - Adam Smith (Georgian/Financial)
  // Era: Georgian Financial
  // ==========================================
  economics: {
    id: 'economics',
    name: 'Economics',
    icon: '📊',
    concept: 'Financial & Analytical',
    era: 'georgian-financial',
    mood: 'dark',

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

    colors: {
      primary: '#22C55E',
      primaryDark: '#16A34A',
      primaryLight: '#4ADE80',
      bgPrimary: '#052E16',
      bgSecondary: '#14532D',
      bgTertiary: '#166534',
      textPrimary: '#DCFCE7',
      textSecondary: '#BBF7D0',
      textMuted: '#86EFAC',
      accent: '#22C55E',
      accentLight: '#4ADE80',
      accentDark: '#16A34A',
      border: '#166534',
      borderLight: '#15803D',
    },

    classes: {
      pageBg: 'bg-gradient-to-br from-[#052E16] via-[#14532D] to-[#052E16]',
      headerBg: 'bg-gradient-to-r from-[#14532D]/95 to-[#052E16]/95',
      headerText: 'text-white',
      headerOverlay: 'from-green-900/40 via-emerald-900/50 to-green-950/70',
      userMsgBg: 'bg-green-900/40',
      userMsgBorder: 'border-green-700/50',
      userMsgText: 'text-green-100',
      aiMsgBg: 'bg-emerald-950/60',
      aiMsgAccent: 'text-green-300',
      aiMsgBorder: 'border-green-700/30',
      inputBg: 'bg-emerald-950/80',
      inputBorder: 'border-green-700',
      inputFocus: 'focus-within:border-green-500 focus-within:ring-2 focus-within:ring-green-500/20',
      inputText: 'text-green-100',
      inputPlaceholder: 'placeholder-green-400',
      sendBtn: 'bg-green-600 hover:bg-green-500 text-white',
      sidebarBg: 'bg-green-950/95',
      sidebarBorder: 'border-green-800',
      sidebarText: 'text-green-100',
      sidebarTextMuted: 'text-green-400',
      activeItem: 'bg-green-900/50 border-l-2 border-green-500',
      hoverItem: 'hover:bg-green-900/40',
      accent: 'text-green-400',
      accentBg: 'bg-green-600',
      accentHover: 'hover:bg-green-500',
      accentLight: 'bg-green-900/30',
      codeBlockBg: 'bg-green-950',
      blockquoteBorder: 'border-l-4 border-green-500',
      scrollbarTrack: 'scrollbar-track-green-950',
      scrollbarThumb: 'scrollbar-thumb-green-600',
      welcomeBg: 'bg-green-950/80',
      welcomeBorder: 'border-green-800',
      optionPillBg: 'bg-green-900/80',
      optionPillBorder: 'border-green-700',
      optionPillActive: 'bg-green-600/30 border-green-500',
    },

    particles: {
      type: 'coins',
      count: 25,
      colors: ['#22C55E', '#4ADE80', '#86EFAC', '#BBF7D0'],
      speed: 'medium',
      opacity: 0.5,
    },

    background: {
      gradient: 'radial-gradient(ellipse at bottom, #166534 0%, #14532D 50%, #052E16 100%)',
      overlay: 'financial',
    },

  },
};

// ============================================
// DEFAULT THEME (General/No subject)
// Uses Philosophy (Socratic) theme as base
// ============================================
export const DEFAULT_THEME = {
  id: 'general',
  name: 'Scoratis',
  icon: '🏛️',
  concept: 'Athenian Wisdom',
  era: 'athenian-classical',
  mood: 'light',

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

  colors: {
    primary: '#6366F1',
    primaryDark: '#4F46E5',
    primaryLight: '#818CF8',
    bgPrimary: '#F5F0E6',
    bgSecondary: '#FAF6ED',
    bgTertiary: '#EBE5D8',
    textPrimary: '#1E1B4B',
    textSecondary: '#312E81',
    textMuted: '#4338CA',
    accent: '#6366F1',
    accentLight: '#818CF8',
    accentDark: '#4F46E5',
    border: '#D4CFB8',
    borderLight: '#E7E5E4',
  },

  classes: {
    pageBg: 'bg-gradient-to-br from-[#F5F0E6] via-[#FAF6ED] to-[#EBE5D8]',
    headerBg: 'bg-gradient-to-r from-[#2a2a2a]/95 to-[#1a1a1a]/95',
    headerText: 'text-white',
    headerOverlay: 'from-indigo-900/30 via-slate-900/50 to-slate-900/60',
    userMsgBg: 'bg-indigo-100/60',
    userMsgBorder: 'border-indigo-200',
    userMsgText: 'text-indigo-900',
    aiMsgBg: 'bg-white/70',
    aiMsgAccent: 'text-indigo-700',
    aiMsgBorder: 'border-gray-200',
    inputBg: 'bg-white/90',
    inputBorder: 'border-gray-300',
    inputFocus: 'focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-200',
    inputText: 'text-gray-900',
    inputPlaceholder: 'placeholder-gray-400',
    sendBtn: 'bg-indigo-600 hover:bg-indigo-500 text-white',
    sidebarBg: 'bg-[#faf6ed]/95',
    sidebarBorder: 'border-gray-200',
    sidebarText: 'text-gray-900',
    sidebarTextMuted: 'text-gray-500',
    activeItem: 'bg-indigo-100 border-l-2 border-indigo-600',
    hoverItem: 'hover:bg-gray-100',
    accent: 'text-indigo-600',
    accentBg: 'bg-indigo-600',
    accentHover: 'hover:bg-indigo-500',
    accentLight: 'bg-indigo-100',
    codeBlockBg: 'bg-gray-50',
    blockquoteBorder: 'border-l-4 border-indigo-500',
    scrollbarTrack: 'scrollbar-track-gray-100',
    scrollbarThumb: 'scrollbar-thumb-indigo-400',
    welcomeBg: 'bg-white/80',
    welcomeBorder: 'border-gray-200',
    optionPillBg: 'bg-white/80',
    optionPillBorder: 'border-gray-300',
    optionPillActive: 'bg-indigo-100 border-indigo-500',
  },

  particles: {
    type: 'rays',
    count: 15,
    colors: ['#6366F1', '#818CF8', '#A5B4FC', '#C7D2FE'],
    speed: 'slow',
    opacity: 0.3,
  },

  background: {
    gradient: 'radial-gradient(ellipse at top, #FFFFFF 0%, #FAF6ED 50%, #F5F0E6 100%)',
    overlay: 'marble',
  },
};

// ============================================
// HELPER FUNCTIONS
// ============================================

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
 * @param {string} colorName - The color name (e.g., 'primary', 'bgPrimary')
 * @returns {string} Hex color value
 */
export function getThemeColor(subjectId, colorName) {
  const theme = getSubjectTheme(subjectId);
  return theme.colors[colorName] || DEFAULT_THEME.colors[colorName] || '#6366F1';
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

/**
 * Get particle configuration for a subject
 * @param {string} subjectId - The subject ID
 * @returns {object} Particle configuration object
 */
export function getParticleConfig(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.particles || DEFAULT_THEME.particles;
}

/**
 * Get background configuration for a subject
 * @param {string} subjectId - The subject ID
 * @returns {object} Background configuration object
 */
export function getBackgroundConfig(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.background || DEFAULT_THEME.background;
}

/**
 * Check if theme is dark mode
 * @param {string} subjectId - The subject ID
 * @returns {boolean} True if dark theme
 */
export function isDarkTheme(subjectId) {
  const theme = getSubjectTheme(subjectId);
  return theme.mood === 'dark' || theme.mood === 'cool';
}

/**
 * Available particle types
 */
export const PARTICLE_TYPES = [
  'stars',    // Physics
  'bubbles',  // Chemistry
  'cells',    // Biology
  'shapes',   // Mathematics
  'binary',   // Computer Science
  'quills',   // English
  'dust',     // History
  'rays',     // Philosophy
  'neurons',  // Psychology
  'coins',    // Economics
];

export default SUBJECT_THEMES;
