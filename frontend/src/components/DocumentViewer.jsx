import { useState, useEffect, useRef, useMemo } from 'react';
import {
  FileText, Image, File, ChevronLeft, ChevronRight,
  ZoomIn, ZoomOut, RotateCw, Download, Loader2,
  AlertCircle, Search, Copy, Check
} from 'lucide-react';

// PDF Viewer - Simple text-based preview (for full PDF viewing, use react-pdf library)
function PDFPreview({ content, pageNumber, totalPages, onPageChange }) {
  return (
    <div className="flex flex-col h-full">
      {/* PDF content */}
      <div className="flex-1 overflow-y-auto p-6 bg-white">
        <div className="prose prose-sm max-w-none">
          <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans leading-relaxed">
            {content}
          </pre>
        </div>
      </div>

      {/* Page navigation */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 px-4 py-3 border-t border-gray-200 bg-gray-50">
          <button
            onClick={() => onPageChange?.(Math.max(1, pageNumber - 1))}
            disabled={pageNumber <= 1}
            className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-sm text-gray-600">
            Page {pageNumber} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange?.(Math.min(totalPages, pageNumber + 1))}
            disabled={pageNumber >= totalPages}
            className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}

// Text/Markdown Viewer with syntax highlighting
function TextViewer({ content, fileType, searchQuery, highlightedChunkId }) {
  const contentRef = useRef(null);
  const [copied, setCopied] = useState(false);

  // Highlight search matches
  const highlightedContent = useMemo(() => {
    if (!searchQuery || !content) return content;

    const regex = new RegExp(`(${searchQuery})`, 'gi');
    return content.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
  }, [content, searchQuery]);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Scroll to highlighted chunk
  useEffect(() => {
    if (highlightedChunkId && contentRef.current) {
      // For text content, we scroll to the first occurrence if possible
      const firstMark = contentRef.current.querySelector('mark');
      if (firstMark) {
        firstMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [highlightedChunkId]);

  return (
    <div ref={contentRef} className="h-full flex flex-col">
      {/* Copy button */}
      <div className="flex justify-end px-4 py-2 border-b border-gray-100">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900
                     hover:bg-gray-100 rounded-lg transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-green-500" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {fileType === 'md' ? (
          <div
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: highlightedContent }}
          />
        ) : (
          <pre
            className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed"
            dangerouslySetInnerHTML={{ __html: highlightedContent }}
          />
        )}
      </div>
    </div>
  );
}

// Image Viewer with zoom/pan
function ImageViewer({ src, alt, zoom, onZoomChange }) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);

  const handleZoomIn = () => onZoomChange?.(Math.min(300, zoom + 25));
  const handleZoomOut = () => onZoomChange?.(Math.max(25, zoom - 25));
  const handleReset = () => onZoomChange?.(100);

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="flex items-center justify-center gap-2 px-4 py-2 border-b border-gray-100">
        <button
          onClick={handleZoomOut}
          disabled={zoom <= 25}
          className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-40 transition-colors"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-sm text-gray-600 min-w-[4rem] text-center">{zoom}%</span>
        <button
          onClick={handleZoomIn}
          disabled={zoom >= 300}
          className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-40 transition-colors"
          title="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-gray-200 mx-2" />
        <button
          onClick={handleReset}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Reset zoom"
        >
          <RotateCw className="w-4 h-4" />
        </button>
      </div>

      {/* Image */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex items-center justify-center bg-gray-100 p-4"
      >
        {isLoading && (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span className="text-sm">Loading image...</span>
          </div>
        )}
        {error && (
          <div className="flex flex-col items-center gap-2 text-red-500">
            <AlertCircle className="w-8 h-8" />
            <span className="text-sm">Failed to load image</span>
          </div>
        )}
        <img
          src={src}
          alt={alt}
          onLoad={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false);
            setError(true);
          }}
          className={`max-w-full max-h-full object-contain transition-transform ${isLoading || error ? 'hidden' : ''}`}
          style={{ transform: `scale(${zoom / 100})` }}
        />
      </div>
    </div>
  );
}

// Main Document Viewer Component
export function DocumentViewer({
  document,
  zoom = 100,
  onZoomChange,
  searchQuery = '',
  highlightedChunkId,
  className = ''
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  // Get file type
  const fileType = document?.file_type?.toLowerCase() || '';
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(fileType);
  const isPDF = fileType === 'pdf';
  const isText = ['txt', 'md', 'html', 'json', 'xml'].includes(fileType);

  // Get document URL for images
  const getDocumentUrl = () => {
    if (document?.file_path) {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      return `${baseUrl}/v1/documents/${document.id}/file`;
    }
    return null;
  };

  if (!document) {
    return (
      <div className={`flex flex-col items-center justify-center h-full text-gray-500 ${className}`}>
        <File className="w-16 h-16 mb-4 opacity-30" />
        <p className="text-sm">No document selected</p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <p className="text-sm text-gray-500 mt-2">Loading document...</p>
      </div>
    );
  }

  // Image viewer
  if (isImage) {
    const imageUrl = getDocumentUrl();
    return (
      <div className={className}>
        <ImageViewer
          src={imageUrl}
          alt={document.title}
          zoom={zoom}
          onZoomChange={onZoomChange}
        />
      </div>
    );
  }

  // PDF viewer (text preview)
  if (isPDF) {
    return (
      <div className={className}>
        <PDFPreview
          content={document.content}
          pageNumber={currentPage}
          totalPages={document.total_pages || 1}
          onPageChange={setCurrentPage}
        />
      </div>
    );
  }

  // Text/Markdown viewer
  return (
    <div className={className}>
      <TextViewer
        content={document.content}
        fileType={fileType}
        searchQuery={searchQuery}
        highlightedChunkId={highlightedChunkId}
      />
    </div>
  );
}

// Document Info Card - shows document metadata
export function DocumentInfoCard({ document }) {
  if (!document) return null;

  const formatBytes = (bytes) => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
      <h4 className="text-sm font-semibold text-gray-900 mb-3">Document Info</h4>
      <div className="space-y-2 text-sm">
        <InfoRow label="Title" value={document.title || 'Untitled'} />
        <InfoRow label="Type" value={document.file_type?.toUpperCase() || 'Unknown'} />
        <InfoRow label="Size" value={formatBytes(document.file_size)} />
        <InfoRow label="Chunks" value={document.chunks?.length || 0} />
        <InfoRow label="Created" value={formatDate(document.created_at)} />
        {document.status && (
          <InfoRow
            label="Status"
            value={
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                document.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                document.status === 'PROCESSING' ? 'bg-yellow-100 text-yellow-700' :
                document.status === 'ERROR' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {document.status}
              </span>
            }
          />
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{value}</span>
    </div>
  );
}

export default DocumentViewer;
