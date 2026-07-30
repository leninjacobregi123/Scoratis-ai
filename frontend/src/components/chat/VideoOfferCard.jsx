import React from 'react';
import { Film, Play } from 'lucide-react';

export default function VideoOfferCard({ recommendation, onAccept, onDismiss }) {
  if (!recommendation || !recommendation.available) return null;

  const { topic, concepts = [], type } = recommendation;

  const typeLabels = {
    process: 'Process',
    structure: 'Structure',
    concept: 'Concept',
    comparison: 'Comparison',
    transformation: 'Transformation'
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mt-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
          <Film className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-blue-900">Visual Explanation Available</h4>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              15-30s
            </span>
          </div>

          {topic && (
            <p className="text-sm text-blue-800 font-medium mb-2">{topic}</p>
          )}

          {type && typeLabels[type] && (
            <span className="inline-block text-xs bg-white/70 text-blue-700 px-2 py-0.5 rounded mb-2">
              {typeLabels[type]}
            </span>
          )}

          {concepts.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {concepts.slice(0, 3).map((concept, i) => (
                <span key={i} className="text-xs px-2 py-0.5 bg-white rounded-full text-gray-700 border border-gray-200">
                  {concept}
                </span>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={onAccept}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 shadow-sm"
            >
              <Play className="w-4 h-4" />
              Generate Video
            </button>
            <button
              onClick={onDismiss}
              className="px-4 py-2 bg-white text-gray-600 text-sm rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
            >
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
