import React from 'react';
import { MessageCircle } from 'lucide-react';

const GalleryWelcomeDialog = ({ show, greetingText, onClose }) => {
  if (!show) return null;

  return (
    <div className="absolute bottom-12 left-1/2 -translate-x-1/2 z-40 w-full max-w-2xl px-4 animate-fade-in-up">
      <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute top-0 left-1/4 w-1/2 h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"></div>
        
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-full bg-blue-900/30 flex items-center justify-center border border-blue-700/30 shrink-0">
            <MessageCircle className="w-6 h-6 text-blue-400" />
          </div>
          
          <div className="flex-1">
            <h3 className="text-blue-300 font-serif text-lg mb-1">Socrates</h3>
            <p className="text-slate-200 leading-relaxed text-lg italic">"{greetingText}"</p>
            
            <p className="text-slate-400 text-sm mt-4">
              Explore the halls. Stand before any subject to begin your inquiry.
            </p>
          </div>
          
          <button 
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 p-2"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
};

export default GalleryWelcomeDialog;
