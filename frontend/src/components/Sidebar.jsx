import { Home, MessageCircle, Search, GalleryHorizontalEnd, Settings } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import SocratesLogo from '../3d/SocratesLogo';

const navItems = [
  { id: 'home', label: 'Home', icon: Home, path: '/app/home' },
  { id: 'scoratis', label: 'Scoratis AI', icon: MessageCircle, path: '/app/scoratis', primary: true },
  { id: 'settings', label: 'AI Settings', icon: Settings, path: '/app/settings' },
  // Video Vault hidden from nav but still accessible at /app/videos
];

export default function Sidebar({ stats, showGalleryLink = false }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col p-5 bg-bg-secondary border-r border-border-color">
      {/* Logo */}
      <div className="flex items-center space-x-3 mb-8">
        <SocratesLogo size={48} />
        <span className="text-xl font-light text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Scoratis</span>
      </div>

      {/* User Profile */}
      <div className="glass-card rounded-xl p-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-accent-olive-light to-accent-olive flex items-center justify-center text-bg-primary font-semibold text-lg">
            L
          </div>
          <div>
            <h2 className="text-text-primary font-semibold">Lenin</h2>
            <p className="text-sm text-text-muted">
              {stats.journals_this_week || 0} entries this week
            </p>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <input
          type="text"
          placeholder="Search..."
          className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 pl-11 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-olive transition-colors"
        />
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
      </div>

      {/* Navigation */}
      <nav className="space-y-2 flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.id}
              to={item.path}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${
                isActive
                  ? 'bg-accent-olive/10 text-text-primary border-l-2 border-accent-olive'
                  : item.primary
                  ? 'text-text-secondary hover:text-text-primary hover:bg-accent-olive/5 border border-transparent hover:border-accent-olive/30'
                  : 'text-text-muted hover:text-text-primary hover:bg-bg-card'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-accent-olive' : item.primary ? 'text-accent-olive' : ''}`} />
              <span className="font-medium">{item.label}</span>
              {item.primary && !isActive && (
                <span className="ml-auto text-xs px-2 py-0.5 bg-accent-olive/20 text-accent-olive rounded-full">AI</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Gallery Link */}
      {showGalleryLink && (
        <button
          onClick={() => navigate('/')}
          className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all text-text-muted hover:text-text-primary hover:bg-bg-card mt-2 border border-dashed border-border-color"
        >
          <GalleryHorizontalEnd className="w-5 h-5" />
          <span className="font-medium">Enter Gallery</span>
        </button>
      )}

      {/* Quick Stats */}
      <div className="glass-card rounded-xl p-4 mt-4">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          Quick Stats
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center">
            <div className="text-2xl font-semibold text-text-primary">
              {stats.total_journals || 0}
            </div>
            <div className="text-xs text-text-muted">Journals</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-semibold text-text-primary">
              {stats.total_folders || 0}
            </div>
            <div className="text-xs text-text-muted">Folders</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
