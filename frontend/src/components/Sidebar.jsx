import { Home, MessageCircle, Search, GalleryHorizontalEnd, Settings, ChevronLeft, ChevronRight, Clock, Plus } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import SocratesLogo from '../3d/SocratesLogo';

const navItems = [
  { id: 'home', label: 'Home', icon: Home, path: '/app/home' },
  { id: 'scoratis', label: 'Scoratis AI', icon: MessageCircle, path: '/app/scoratis', primary: true },
  { id: 'settings', label: 'AI Settings', icon: Settings, path: '/app/settings' },
];

export default function Sidebar({
  stats,
  showGalleryLink = false,
  collapsed = false,
  onToggle,
  recentChats = [],
  onNewChat,
  onSelectChat,
  activeSessionId
}) {
  const navigate = useNavigate();
  const location = useLocation();

  // Show only 5 most recent chats
  const displayChats = recentChats.slice(0, 5);

  return (
    <aside className={`${collapsed ? 'w-16' : 'w-72'} flex-shrink-0 flex flex-col ${collapsed ? 'p-2' : 'p-5'} bg-bg-secondary border-r border-border-color transition-all duration-300 ease-in-out relative`}>
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="absolute -right-4 top-8 w-8 h-8 rounded-full bg-accent-olive text-white flex items-center justify-center shadow-lg hover:bg-accent-olive-dark transition-colors z-50 border-2 border-white"
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
      </button>

      {/* Logo */}
      <div className={`flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} mb-6`}>
        <SocratesLogo size={collapsed ? 32 : 48} />
        {!collapsed && (
          <span className="text-xl font-light text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Scoratis</span>
        )}
      </div>

      {/* User Profile - Hidden when collapsed */}
      {!collapsed && (
        <div className="glass-card rounded-xl p-3 mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-olive-light to-accent-olive flex items-center justify-center text-bg-primary font-semibold">
              L
            </div>
            <div>
              <h2 className="text-text-primary font-semibold text-sm">Lenin</h2>
              <p className="text-xs text-text-muted">
                {stats.journals_this_week || 0} entries this week
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Collapsed User Avatar */}
      {collapsed && (
        <div className="flex justify-center mb-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-olive-light to-accent-olive flex items-center justify-center text-bg-primary font-semibold">
            L
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="space-y-1 mb-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.id}
              to={item.path}
              title={collapsed ? item.label : undefined}
              className={`w-full flex items-center ${collapsed ? 'justify-center px-2' : 'space-x-3 px-4'} py-2.5 rounded-xl transition-all ${
                isActive
                  ? 'bg-accent-olive/10 text-text-primary border-l-2 border-accent-olive'
                  : item.primary
                  ? 'text-text-secondary hover:text-text-primary hover:bg-accent-olive/5 border border-transparent hover:border-accent-olive/30'
                  : 'text-text-muted hover:text-text-primary hover:bg-bg-card'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-accent-olive' : item.primary ? 'text-accent-olive' : ''}`} />
              {!collapsed && (
                <>
                  <span className="font-medium text-sm">{item.label}</span>
                  {item.primary && !isActive && (
                    <span className="ml-auto text-xs px-2 py-0.5 bg-accent-olive/20 text-accent-olive rounded-full">AI</span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Recent Chats Section - Hidden when collapsed */}
      {!collapsed && location.pathname.includes('/app/scoratis') && (
        <div className="flex-1 flex flex-col min-h-0 mb-4">
          {/* Header with New Chat button */}
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3 h-3" />
              Recent Chats
            </h3>
            {onNewChat && (
              <button
                onClick={onNewChat}
                className="p-1 rounded-md hover:bg-accent-olive/10 text-text-muted hover:text-accent-olive transition-colors"
                title="New chat"
              >
                <Plus className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Chat List */}
          <div className="flex-1 overflow-y-auto space-y-1">
            {displayChats.length > 0 ? (
              displayChats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => onSelectChat?.(chat.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-all text-sm truncate ${
                    activeSessionId === chat.id
                      ? 'bg-accent-olive/15 text-text-primary border-l-2 border-accent-olive'
                      : 'text-text-muted hover:text-text-primary hover:bg-bg-card'
                  }`}
                  title={chat.title || 'Untitled chat'}
                >
                  <div className="truncate">
                    {chat.title || 'New conversation'}
                  </div>
                  {chat.updated_at && (
                    <div className="text-xs text-text-muted/60 mt-0.5">
                      {new Date(chat.updated_at).toLocaleDateString()}
                    </div>
                  )}
                </button>
              ))
            ) : (
              <div className="text-xs text-text-muted text-center py-4">
                No recent chats
              </div>
            )}
          </div>
        </div>
      )}

      {/* Collapsed chat icon */}
      {collapsed && location.pathname.includes('/app/scoratis') && (
        <button
          onClick={onNewChat}
          className="flex justify-center p-2 mb-4 rounded-lg hover:bg-accent-olive/10 text-text-muted hover:text-accent-olive transition-colors"
          title="New chat"
        >
          <Plus className="w-5 h-5" />
        </button>
      )}

      {/* Gallery Link */}
      {showGalleryLink && (
        <button
          onClick={() => navigate('/')}
          title={collapsed ? "Enter Gallery" : undefined}
          className={`w-full flex items-center ${collapsed ? 'justify-center px-2' : 'space-x-3 px-4'} py-2.5 rounded-xl transition-all text-text-muted hover:text-text-primary hover:bg-bg-card border border-dashed border-border-color`}
        >
          <GalleryHorizontalEnd className="w-5 h-5" />
          {!collapsed && <span className="font-medium text-sm">Enter Gallery</span>}
        </button>
      )}

      {/* Quick Stats - Hidden when collapsed */}
      {!collapsed && (
        <div className="glass-card rounded-xl p-3 mt-4">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
            Quick Stats
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <div className="text-center">
              <div className="text-xl font-semibold text-text-primary">
                {stats.total_journals || 0}
              </div>
              <div className="text-xs text-text-muted">Journals</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-semibold text-text-primary">
                {stats.total_folders || 0}
              </div>
              <div className="text-xs text-text-muted">Folders</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
