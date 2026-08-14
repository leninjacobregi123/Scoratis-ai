import { useState } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import { MessageCircle, Lightbulb, Sparkles, ChevronRight } from 'lucide-react';

export default function Home() {
  const { stats } = useOutletContext();
  const navigate = useNavigate();
  const [hoveredFeature, setHoveredFeature] = useState(null);

  return (
    <div className="h-full overflow-y-auto relative">
      {/* Subtle Background Elements */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 -right-64 w-[800px] h-[800px] bg-accent-olive/[0.03] rounded-full blur-[150px]" />
        <div className="absolute bottom-0 -left-32 w-[600px] h-[600px] bg-accent-olive/[0.05] rounded-full blur-[120px]" />
      </div>

      {/* Hero Section - Elegant Socratic Design */}
      <section className="relative min-h-[85vh] flex items-center">
        <div className="w-full max-w-7xl mx-auto px-8 py-16">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left Column - Content */}
            <div className="relative z-10">
              {/* Badge */}
              <div className="inline-flex items-center space-x-2 mb-10">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-olive opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-accent-olive"></span>
                </span>
                <span className="px-4 py-2 bg-bg-card/80 backdrop-blur-sm border border-border-color rounded-full text-text-secondary text-sm font-semibold tracking-wider uppercase">
                  Socratic Learning Engine
                </span>
              </div>

              {/* Main Quote */}
              <h1 className="mb-8">
                <span className="block text-5xl md:text-6xl lg:text-7xl font-light text-text-primary leading-[1.1] tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>
                  The unexamined
                </span>
                <span className="block text-5xl md:text-6xl lg:text-7xl font-light text-text-primary leading-[1.1] tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>
                  life
                </span>
                <span className="block text-5xl md:text-6xl lg:text-7xl font-light italic text-accent-olive leading-[1.1] tracking-tight mt-2" style={{ fontFamily: 'Georgia, serif' }}>
                  is not worth living.
                </span>
              </h1>

              {/* Description */}
              <p className="text-xl text-text-secondary max-w-xl mb-12 leading-relaxed">
                Engage in AI-guided Socratic questioning and unlock deeper understanding through rigorous inquiry.
              </p>

              {/* CTA Buttons */}
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={() => navigate('/app/scoratis')}
                  className="group flex items-center space-x-3 px-8 py-4 bg-accent-olive hover:bg-accent-olive-dark text-white font-semibold rounded-xl shadow-lg shadow-accent-olive/20 hover:shadow-xl hover:shadow-accent-olive/30 hover:scale-[1.02] active:scale-[0.98] transition-all duration-300"
                >
                  <Lightbulb className="w-5 h-5" />
                  <span>Start Learning</span>
                </button>
                <button
                  onClick={() => navigate('/app/videos')}
                  className="group flex items-center space-x-3 px-8 py-4 bg-bg-card hover:bg-bg-tertiary border border-border-color hover:border-accent-olive text-text-primary font-semibold rounded-xl transition-all duration-300"
                >
                  <Sparkles className="w-5 h-5 text-accent-olive" />
                  <span>Explore Videos</span>
                </button>
              </div>
            </div>

            {/* Right Column - Socrates Bust Image */}
            <div className="relative flex items-center justify-center lg:justify-end">
              {/* Subtle glow behind the bust */}
              <div className="absolute w-[500px] h-[500px] bg-gradient-radial from-accent-olive/20 via-accent-olive/10 to-transparent rounded-full blur-3xl" />
              <img
                src="/socrates-nobg.png"
                alt="Socrates"
                className="relative w-[550px] h-auto object-contain drop-shadow-2xl"
                style={{
                  filter: 'drop-shadow(0 25px 50px rgba(107, 124, 94, 0.3))'
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="relative z-10 py-8 border-y border-border-color/30 bg-bg-card/30 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-8">
          <div className="flex flex-wrap justify-center gap-16">
            <StatItem icon={MessageCircle} label="Conversations" value={stats.total_conversations || 0} />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 py-24 px-8">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <div className="text-center mb-16">
            <span className="inline-block px-4 py-2 bg-accent-olive/10 border border-accent-olive/20 rounded-full text-accent-olive text-sm font-semibold mb-6">
              Powerful Features
            </span>
            <h2 className="text-4xl md:text-5xl font-light text-text-primary mb-4" style={{ fontFamily: 'Georgia, serif' }}>
              Everything you need to
              <span className="italic text-accent-olive"> accelerate learning</span>
            </h2>
            <p className="text-text-muted text-lg max-w-2xl mx-auto">
              A complete toolkit for deep thinking and AI-powered discovery
            </p>
          </div>

          {/* Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <FeatureCard
              icon={MessageCircle}
              gradient="from-accent-olive to-accent-olive-dark"
              title="Socratic AI Coach"
              description="Learn through guided questioning. Our AI helps you reach deeper understanding through the Socratic method."
              features={['Guided discovery', 'Concept clarification', 'Memory persistence']}
              onClick={() => navigate('/app/scoratis')}
              index={0}
              hoveredFeature={hoveredFeature}
              setHoveredFeature={setHoveredFeature}
            />
            <FeatureCard
              icon={Sparkles}
              gradient="from-purple-500 to-violet-600"
              title="Video Vault"
              description="Generate educational videos with AI or discover content from across the web to enhance your learning."
              features={['AI video generation', 'Content discovery', 'Watch history']}
              onClick={() => navigate('/app/videos')}
              index={1}
              hoveredFeature={hoveredFeature}
              setHoveredFeature={setHoveredFeature}
            />
          </div>
        </div>
      </section>

      {/* Footer Quote */}
      <section className="relative z-10 py-20 px-8 border-t border-border-color/30">
        <div className="max-w-4xl mx-auto text-center">
          <blockquote className="text-3xl md:text-4xl font-light text-text-primary italic mb-6" style={{ fontFamily: 'Georgia, serif' }}>
            "I cannot teach anybody anything. I can only make them think."
          </blockquote>
          <p className="text-text-muted">— Socrates</p>
        </div>
      </section>
    </div>
  )
}

// Stat Item Component
function StatItem({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center space-x-4">
      <div className="w-10 h-10 rounded-xl bg-accent-olive/10 flex items-center justify-center">
        <Icon className="w-5 h-5 text-accent-olive" />
      </div>
      <div>
        <div className="text-2xl font-bold text-text-primary">{value}</div>
        <div className="text-sm text-text-muted">{label}</div>
      </div>
    </div>
  )
}

// Feature Card Component
function FeatureCard({ icon: Icon, gradient, title, description, features, onClick, index, hoveredFeature, setHoveredFeature }) {
  const isHovered = hoveredFeature === index

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHoveredFeature(index)}
      onMouseLeave={() => setHoveredFeature(null)}
      className="group relative bg-bg-card border border-border-color rounded-3xl p-8 cursor-pointer transition-all duration-500 hover:border-transparent hover:shadow-2xl hover:shadow-accent-olive/10 hover:-translate-y-2"
    >
      {/* Hover Background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} rounded-3xl opacity-0 group-hover:opacity-[0.03] transition-opacity duration-500`} />

      {/* Icon */}
      <div className={`relative w-16 h-16 rounded-2xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-6 shadow-lg transition-all duration-500 group-hover:scale-110 group-hover:rotate-3`}>
        <Icon className="w-8 h-8 text-white" />
      </div>

      {/* Content */}
      <h3 className="text-xl font-bold text-text-primary mb-3 group-hover:text-accent-olive transition-colors" style={{ fontFamily: 'Georgia, serif' }}>
        {title}
      </h3>
      <p className="text-text-secondary mb-6 leading-relaxed">{description}</p>

      {/* Features List */}
      <ul className="space-y-3">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center space-x-3 text-sm text-text-muted">
            <span className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${gradient}`} />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      {/* Arrow */}
      <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all duration-300">
        <ChevronRight className="w-5 h-5 text-accent-olive" />
      </div>
    </div>
  )
}
