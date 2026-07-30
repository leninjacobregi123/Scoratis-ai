import React, { useState } from 'react';
import { MoreVertical, Edit2, Trash2, Check, X } from 'lucide-react';

export default function ConversationItem({ conversation, isActive, onClick, onDelete, onRename, isDark }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(conversation.title);
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      className={`group relative flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${
        isActive
          ? isDark ? 'bg-white/10 text-white border-l-2 border-white/50' : 'bg-gray-100 text-text-primary border-l-2 border-gray-800'
          : isDark ? 'hover:bg-white/5 text-gray-300' : 'hover:bg-bg-tertiary text-text-secondary'
      }`}
      onClick={() => !isEditing && onClick(conversation.id)}
    >
      {isEditing ? (
        <div className="flex-1 flex items-center gap-2">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className={`flex-1 px-3 py-1.5 rounded-lg text-sm outline-none border ${isDark ? 'bg-white/10 text-white border-white/20' : 'bg-bg-card text-text-primary border-gray-400'}`}
            onClick={(e) => e.stopPropagation()}
            autoFocus
          />
          <button onClick={(e) => { e.stopPropagation(); onRename(conversation.id, editTitle); setIsEditing(false); }} className={`${isDark ? 'text-green-400 hover:text-green-300' : 'text-gray-600 hover:text-gray-900'}`}>
            <Check className="w-4 h-4" />
          </button>
          <button onClick={(e) => { e.stopPropagation(); setIsEditing(false); }} className={`${isDark ? 'text-gray-400 hover:text-white' : 'text-text-muted hover:text-text-primary'}`}>
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <>
          <span className="text-sm truncate flex-1">
            {conversation.title || 'New conversation'}
          </span>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <button onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }} className={`p-1.5 rounded-lg ${isDark ? 'hover:bg-white/10' : 'hover:bg-bg-card'}`}>
              <MoreVertical className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-text-muted'}`} />
            </button>
            {showMenu && (
              <div className={`absolute right-2 top-full mt-1 rounded-xl shadow-xl z-50 py-1.5 min-w-[120px] ${isDark ? 'bg-gray-800 border border-white/10' : 'bg-bg-card border border-border-color'}`}>
                <button onClick={(e) => { e.stopPropagation(); setIsEditing(true); setShowMenu(false); }} className={`w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors ${isDark ? 'text-gray-300 hover:bg-white/10 hover:text-white' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}>
                  <Edit2 className="w-3.5 h-3.5" /> Rename
                </button>
                <button onClick={(e) => { e.stopPropagation(); onDelete(conversation.id); setShowMenu(false); }} className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 transition-colors ${isDark ? 'hover:bg-red-500/10' : 'hover:bg-red-50'}`}>
                  <Trash2 className="w-3.5 h-3.5" /> Delete
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
