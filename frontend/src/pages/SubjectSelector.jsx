import { useNavigate } from 'react-router-dom';
import { BookOpen, Atom, FlaskConical, Heart, Calculator, Code, BookText, Clock, Brain, Lightbulb, DollarSign } from 'lucide-react';

const SUBJECTS = [
  { id: 'physics', name: 'Physics', icon: Atom, color: 'blue', description: 'Explore the universe' },
  { id: 'chemistry', name: 'Chemistry', icon: FlaskConical, color: 'emerald', description: 'Matter and reactions' },
  { id: 'biology', name: 'Biology', icon: Heart, color: 'pink', description: 'Life and organisms' },
  { id: 'mathematics', name: 'Mathematics', icon: Calculator, color: 'violet', description: 'Numbers and patterns' },
  { id: 'computer_science', name: 'Computer Science', icon: Code, color: 'cyan', description: 'Algorithms and code' },
  { id: 'english', name: 'English', icon: BookText, color: 'amber', description: 'Language and literature' },
  { id: 'history', name: 'History', icon: Clock, color: 'stone', description: 'Past civilizations' },
  { id: 'philosophy', name: 'Philosophy', icon: Lightbulb, color: 'olive', description: 'Wisdom and reasoning' },
  { id: 'psychology', name: 'Psychology', icon: Brain, color: 'zinc', description: 'Mind and behavior' },
  { id: 'economics', name: 'Economics', icon: DollarSign, color: 'green', description: 'Markets and wealth' }
];

const colorClasses = {
  blue: 'bg-physics-500 hover:bg-physics-600 shadow-glow-blue',
  emerald: 'bg-chemistry-500 hover:bg-chemistry-600 shadow-glow-emerald',
  pink: 'bg-biology-500 hover:bg-biology-600 shadow-glow-pink',
  violet: 'bg-mathematics-500 hover:bg-mathematics-600 shadow-glow-violet',
  cyan: 'bg-computer_science-500 hover:bg-computer_science-600 shadow-glow-cyan',
  amber: 'bg-english-500 hover:bg-english-600 shadow-glow-amber',
  stone: 'bg-history-500 hover:bg-history-600 shadow-glow-stone',
  olive: 'bg-accent-olive hover:bg-accent-olive-dark',
  zinc: 'bg-psychology-500 hover:bg-psychology-600',
  green: 'bg-economics-500 hover:bg-economics-600 shadow-glow-green'
};

export default function SubjectSelector() {
  const navigate = useNavigate();

  const handleSubjectClick = (subjectId) => {
    // Navigate to chat with subject pre-selected
    navigate(`/app/scoratis?subject=${subjectId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-tertiary">
      {/* Header */}
      <header className="border-b border-border-color bg-bg-card/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>
                Scoratis
              </h1>
              <p className="text-text-secondary mt-1">AI-Powered Socratic Learning</p>
            </div>
            <button
              onClick={() => navigate('/app/home')}
              className="px-6 py-2 bg-accent-olive hover:bg-accent-olive-dark text-white rounded-lg transition-colors"
            >
              Dashboard
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-8 py-16 text-center">
        <div className="inline-flex items-center space-x-2 mb-6">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-olive opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-accent-olive"></span>
          </span>
          <span className="px-4 py-2 bg-bg-card/80 backdrop-blur-sm border border-border-color rounded-full text-text-secondary text-sm font-semibold tracking-wider uppercase">
            Choose Your Subject
          </span>
        </div>

        <h2 className="text-5xl md:text-6xl font-light text-text-primary mb-6" style={{ fontFamily: 'Georgia, serif' }}>
          What would you like to{' '}
          <span className="italic text-accent-olive">explore</span>?
        </h2>

        <p className="text-xl text-text-secondary max-w-3xl mx-auto mb-12">
          Select a subject to begin your Socratic learning journey. Each subject features AI-guided questioning 
          tailored to help you discover knowledge through inquiry.
        </p>
      </section>

      {/* Subject Grid */}
      <section className="max-w-7xl mx-auto px-8 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          {SUBJECTS.map((subject) => {
            const Icon = subject.icon;
            const colorClass = colorClasses[subject.color] || colorClasses.olive;

            return (
              <button
                key={subject.id}
                onClick={() => handleSubjectClick(subject.id)}
                className="group relative overflow-hidden bg-bg-card border border-border-color rounded-2xl p-6 hover:shadow-2xl hover:scale-105 transition-all duration-300"
              >
                {/* Icon Circle */}
                <div className={`w-16 h-16 rounded-full ${colorClass} flex items-center justify-center mb-4 mx-auto transition-all duration-300 group-hover:scale-110`}>
                  <Icon className="w-8 h-8 text-white" />
                </div>

                {/* Subject Name */}
                <h3 className="text-xl font-semibold text-text-primary mb-2">
                  {subject.name}
                </h3>

                {/* Description */}
                <p className="text-sm text-text-secondary">
                  {subject.description}
                </p>

                {/* Hover Arrow */}
                <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className={`w-8 h-8 rounded-full ${colorClass} flex items-center justify-center`}>
                    <span className="text-white text-lg">→</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-color bg-bg-card/50 backdrop-blur-sm mt-20">
        <div className="max-w-7xl mx-auto px-8 py-8 text-center text-text-muted">
          <p className="italic" style={{ fontFamily: 'Georgia, serif' }}>
            "The unexamined life is not worth living." — Socrates
          </p>
        </div>
      </footer>
    </div>
  );
}
