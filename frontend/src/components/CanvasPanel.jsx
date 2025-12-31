import { useState, useEffect, useRef } from 'react';
import {
  X, ChevronRight, FileText, File, Image, Search,
  ZoomIn, ZoomOut, Download, Maximize2, Minimize2,
  Book, Layers, ChevronLeft
} from 'lucide-react';

// Canvas Panel - Collapsible right sidebar for document preview
export function CanvasPanel({
  isOpen,
  onClose,
  onToggle,
  documents = [],
  activeDocumentId,
  onSelectDocument,
  highlightedChunkId,
  onOpenDocument,
  className = ''
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const panelRef = useRef(null);

  // Find active document
  const activeDocument = documents.find(d => d.id === activeDocumentId);

  // Filter documents by search
  const filteredDocuments = documents.filter(doc =>
    doc.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.content?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        if (isFullscreen) {
          setIsFullscreen(false);
        } else {
          onClose?.();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isFullscreen, onClose]);

  // Collapsed state - just show toggle button
  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-40
                   bg-white hover:bg-gray-50 border-l border-y border-gray-200
                   rounded-l-lg p-2 shadow-md transition-all hover:pr-3"
        title="Open Documents Panel"
      >
        <ChevronLeft className="w-5 h-5 text-gray-600" />
      </button>
    );
  }

  return (
    <>
      {/* Backdrop for fullscreen mode */}
      {isFullscreen && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsFullscreen(false)}
        />
      )}

      {/* Panel */}
      <div
        ref={panelRef}
        className={`
          fixed right-0 top-0 h-full bg-white border-l border-gray-200 shadow-xl
          flex flex-col z-50 transition-all duration-300 ease-out
          ${isFullscreen ? 'w-[80vw] max-w-5xl' : 'w-96'}
          ${className}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Book className="w-5 h-5 text-gray-600" />
            <h3 className="font-semibold text-gray-900">Documents</h3>
            {documents.length > 0 && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {documents.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4 text-gray-500" />
              ) : (
                <Maximize2 className="w-4 h-4 text-gray-500" />
              )}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              title="Close panel"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="px-4 py-3 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg
                         text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Document List (when no document selected) */}
        {!activeDocument && (
          <div className="flex-1 overflow-y-auto">
            {filteredDocuments.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 p-8">
                <Layers className="w-12 h-12 mb-3 opacity-50" />
                <p className="text-sm text-center">
                  {documents.length === 0
                    ? 'No documents uploaded yet'
                    : 'No documents match your search'
                  }
                </p>
                {documents.length === 0 && (
                  <p className="text-xs text-gray-400 mt-2 text-center">
                    Upload documents to see them here and reference them in your conversations.
                  </p>
                )}
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredDocuments.map(doc => (
                  <DocumentListItem
                    key={doc.id}
                    document={doc}
                    isActive={doc.id === activeDocumentId}
                    onClick={() => onSelectDocument?.(doc.id)}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Document Viewer (when document selected) */}
        {activeDocument && (
          <>
            {/* Document header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 bg-gray-50">
              <button
                onClick={() => onSelectDocument?.(null)}
                className="p-1 hover:bg-gray-200 rounded transition-colors"
                title="Back to list"
              >
                <ChevronLeft className="w-5 h-5 text-gray-600" />
              </button>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {activeDocument.title}
                </p>
                <p className="text-xs text-gray-500">
                  {activeDocument.chunks?.length || 0} chunks
                </p>
              </div>
              {/* Zoom controls */}
              <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 px-2 py-1">
                <button
                  onClick={() => setZoom(Math.max(50, zoom - 10))}
                  className="p-1 hover:bg-gray-100 rounded transition-colors"
                  disabled={zoom <= 50}
                >
                  <ZoomOut className="w-4 h-4 text-gray-500" />
                </button>
                <span className="text-xs text-gray-600 min-w-[3rem] text-center">
                  {zoom}%
                </span>
                <button
                  onClick={() => setZoom(Math.min(200, zoom + 10))}
                  className="p-1 hover:bg-gray-100 rounded transition-colors"
                  disabled={zoom >= 200}
                >
                  <ZoomIn className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            {/* Document content */}
            <div
              className="flex-1 overflow-y-auto p-4"
              style={{ fontSize: `${zoom}%` }}
            >
              <DocumentContent
                document={activeDocument}
                highlightedChunkId={highlightedChunkId}
              />
            </div>
          </>
        )}
      </div>
    </>
  );
}

// Document list item
function DocumentListItem({ document, isActive, onClick }) {
  const getFileIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-5 h-5 text-red-500" />;
      case 'docx':
      case 'doc':
        return <FileText className="w-5 h-5 text-blue-500" />;
      case 'txt':
      case 'md':
        return <FileText className="w-5 h-5 text-gray-500" />;
      case 'png':
      case 'jpg':
      case 'jpeg':
        return <Image className="w-5 h-5 text-green-500" />;
      default:
        return <File className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 p-4 hover:bg-gray-50 transition-colors text-left
                  ${isActive ? 'bg-blue-50 border-l-4 border-blue-500' : ''}`}
    >
      <div className="flex-shrink-0 w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
        {getFileIcon(document.file_type)}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {document.title || 'Untitled Document'}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">
          {document.file_type?.toUpperCase()} · {document.chunks?.length || 0} chunks
        </p>
        {document.summary && (
          <p className="text-xs text-gray-400 mt-1 line-clamp-2">
            {document.summary}
          </p>
        )}
      </div>
      <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0 mt-1" />
    </button>
  );
}

// Document content viewer
function DocumentContent({ document, highlightedChunkId }) {
  const contentRef = useRef(null);

  // Scroll to highlighted chunk
  useEffect(() => {
    if (highlightedChunkId && contentRef.current) {
      const element = contentRef.current.querySelector(`[data-chunk-id="${highlightedChunkId}"]`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [highlightedChunkId]);

  // If document has chunks, display them
  if (document.chunks && document.chunks.length > 0) {
    return (
      <div ref={contentRef} className="space-y-4">
        {document.chunks.map((chunk, index) => (
          <ChunkBlock
            key={chunk.id || index}
            chunk={chunk}
            index={index}
            isHighlighted={chunk.id === highlightedChunkId || `chunk_${chunk.id}` === highlightedChunkId}
          />
        ))}
      </div>
    );
  }

  // Fallback to full content
  if (document.content) {
    return (
      <div className="prose prose-sm max-w-none">
        <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
          {document.content}
        </pre>
      </div>
    );
  }

  return (
    <div className="text-center text-gray-500 py-8">
      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
      <p className="text-sm">Document content not available</p>
    </div>
  );
}

// Chunk block - displays a single chunk with citation number
function ChunkBlock({ chunk, index, isHighlighted }) {
  return (
    <div
      data-chunk-id={chunk.id || `chunk_${index}`}
      className={`
        relative p-4 rounded-lg border transition-all
        ${isHighlighted
          ? 'bg-yellow-50 border-yellow-300 ring-2 ring-yellow-200'
          : 'bg-white border-gray-200 hover:border-gray-300'
        }
      `}
    >
      {/* Citation number badge */}
      <div className="absolute -top-2 -left-2 w-6 h-6 bg-blue-500 text-white rounded-full
                      flex items-center justify-center text-xs font-bold shadow-sm">
        {index + 1}
      </div>

      {/* Chunk content */}
      <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap pl-4">
        {chunk.content}
      </div>

      {/* Metadata */}
      {chunk.page_number && (
        <div className="mt-2 text-xs text-gray-400">
          Page {chunk.page_number}
        </div>
      )}
    </div>
  );
}

// Canvas toggle button (for use in headers)
export function CanvasToggleButton({ isOpen, onClick, documentCount = 0 }) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all
        ${isOpen
          ? 'bg-blue-100 text-blue-700'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }
      `}
      title={isOpen ? 'Close documents panel' : 'Open documents panel'}
    >
      <Book className="w-4 h-4" />
      <span>Docs</span>
      {documentCount > 0 && (
        <span className={`text-xs px-1.5 py-0.5 rounded-full ${isOpen ? 'bg-blue-200' : 'bg-gray-200'}`}>
          {documentCount}
        </span>
      )}
    </button>
  );
}

export default CanvasPanel;
