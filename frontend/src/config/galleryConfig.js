import physicsImg from '../assets/subjects/physics.jpg';
import chemistryImg from '../assets/subjects/chemistry.jpg';
import biologyImg from '../assets/subjects/biology.jpg';
import mathematicsImg from '../assets/subjects/mathematics.jpg';
import computerScienceImg from '../assets/subjects/computer_science.jpg';
import englishImg from '../assets/subjects/english.jpg';
import historyImg from '../assets/subjects/history.jpg';
import philosophyImg from '../assets/subjects/philosophy.jpg';
import psychologyImg from '../assets/subjects/psychology.jpg';
import economicsImg from '../assets/subjects/economics.jpg';

export const SUBJECT_IMAGES = {
  physics: physicsImg,
  chemistry: chemistryImg,
  biology: biologyImg,
  mathematics: mathematicsImg,
  computer_science: computerScienceImg,
  english: englishImg,
  history: historyImg,
  philosophy: philosophyImg,
  psychology: psychologyImg,
  economics: economicsImg,
};

export const GALLERY_CONFIG = {
  SOCRATES_APPROACH_DISTANCE: 15,
  HALL_WIDTH: 22,
  HALL_DEPTH: 70,
  HALL_HEIGHT: 18,
  INTERACTION_SPOT_DISTANCE: 4,
  INTERACTION_SPOT_RADIUS: 1.5,
  PILLAR_POSITIONS: [22, 14, 6, -2, -10, -18],
  SUBJECT_Z_POSITIONS: [18, 10, 2, -6, -14]
};

export const SUBJECT_CHANNELS = [
  { id: 'physics', name: 'Physics', icon: '⚛️', color: '#3B82F6', description: 'Mechanics, thermodynamics, waves, and quantum', side: 'left', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[0], spotX: -GALLERY_CONFIG.HALL_WIDTH / 2 + GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'chemistry', name: 'Chemistry', icon: '🧪', color: '#10B981', description: 'Elements, reactions, and molecular structures', side: 'left', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[1], spotX: -GALLERY_CONFIG.HALL_WIDTH / 2 + GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'biology', name: 'Biology', icon: '🧬', color: '#EC4899', description: 'Life sciences, cells, genetics, and ecosystems', side: 'left', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[2], spotX: -GALLERY_CONFIG.HALL_WIDTH / 2 + GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'mathematics', name: 'Mathematics', icon: '📐', color: '#8B5CF6', description: 'Algebra, calculus, geometry, and logic', side: 'left', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[3], spotX: -GALLERY_CONFIG.HALL_WIDTH / 2 + GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'computer_science', name: 'Computer Science', icon: '💻', color: '#06B6D4', description: 'Programming, algorithms, and technology', side: 'left', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[4], spotX: -GALLERY_CONFIG.HALL_WIDTH / 2 + GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'english', name: 'English', icon: '📚', color: '#F59E0B', description: 'Literature, writing, and language arts', side: 'right', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[0], spotX: GALLERY_CONFIG.HALL_WIDTH / 2 - GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'history', name: 'History', icon: '🏛️', color: '#78716C', description: 'World history, civilizations, and events', side: 'right', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[1], spotX: GALLERY_CONFIG.HALL_WIDTH / 2 - GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'philosophy', name: 'Philosophy', icon: '🤔', color: '#6366F1', description: 'Ethics, logic, metaphysics, and wisdom', side: 'right', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[2], spotX: GALLERY_CONFIG.HALL_WIDTH / 2 - GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'psychology', name: 'Psychology', icon: '🧠', color: '#F472B6', description: 'Mind, behavior, and human cognition', side: 'right', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[3], spotX: GALLERY_CONFIG.HALL_WIDTH / 2 - GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
  { id: 'economics', name: 'Economics', icon: '📊', color: '#22C55E', description: 'Markets, finance, and economic systems', side: 'right', z: GALLERY_CONFIG.SUBJECT_Z_POSITIONS[4], spotX: GALLERY_CONFIG.HALL_WIDTH / 2 - GALLERY_CONFIG.INTERACTION_SPOT_DISTANCE },
];
