/**
 * InlineImage Component
 *
 * Displays images inline in chat messages.
 * Features:
 * - Lazy loading with blur placeholder
 * - Lightbox/fullscreen view
 * - Caption support
 * - Error handling with retry
 * - Theme-aware styling
 */

import { useState, useRef, useEffect } from 'react';
import {
  Image as ImageIcon,
  Maximize2,
  X,
  Download,
  ExternalLink,
  AlertCircle,
  RefreshCw,
  Loader2,
  ZoomIn,
  ZoomOut
} from 'lucide-react';

/**
 * Image loading states
 */
const ImageStatus = {
  LOADING: 'loading',
  READY: 'ready',
  ERROR: 'error'
};

/**
 * Lightbox/Fullscreen Modal
 */
function ImageLightbox({ src, alt, caption, onClose }) {
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  // Close on escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Prevent body scroll when modal open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.5, 4));
  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.5, 0.5));
    if (zoom <= 1) setPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e) => {
    if (zoom > 1) {
      setIsDragging(true);
      dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y };
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging && zoom > 1) {
      setPosition({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = src;
    link.download = alt || 'image';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex flex-col animate-fade-in"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-black/50">
        <div className="flex items-center gap-3">
          {/* Zoom controls */}
          <button
            onClick={handleZoomOut}
            disabled={zoom <= 0.5}
            className="p-2 rounded-lg hover:bg-white/10 text-white disabled:opacity-50"
            title="Zoom out"
          >
            <ZoomOut size={20} />
          </button>
          <span className="text-white text-sm min-w-[60px] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            disabled={zoom >= 4}
            className="p-2 rounded-lg hover:bg-white/10 text-white disabled:opacity-50"
            title="Zoom in"
          >
            <ZoomIn size={20} />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Download */}
          <button
            onClick={handleDownload}
            className="p-2 rounded-lg hover:bg-white/10 text-white"
            title="Download"
          >
            <Download size={20} />
          </button>

          {/* Open in new tab */}
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg hover:bg-white/10 text-white"
            title="Open in new tab"
          >
            <ExternalLink size={20} />
          </a>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 text-white"
            title="Close"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Image Container */}
      <div
        className="flex-1 flex items-center justify-center overflow-hidden cursor-move"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={src}
          alt={alt || ''}
          className="max-w-full max-h-full object-contain transition-transform duration-200"
          style={{
            transform: `scale(${zoom}) translate(${position.x / zoom}px, ${position.y / zoom}px)`,
            cursor: zoom > 1 ? 'move' : 'default'
          }}
          draggable={false}
        />
      </div>

      {/* Caption */}
      {caption && (
        <div className="px-4 py-3 bg-black/50 text-center">
          <p className="text-white text-sm">{caption}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Loading placeholder with blur effect
 */
function ImagePlaceholder({ aspectRatio, theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <div
      className={`flex items-center justify-center rounded-lg animate-pulse
                  ${themeClasses.bgSecondary || 'bg-gray-100'}`}
      style={{ aspectRatio }}
    >
      <Loader2
        size={24}
        className={`animate-spin ${themeClasses.textMuted || 'text-gray-400'}`}
      />
    </div>
  );
}

/**
 * Error state display
 */
function ImageError({ onRetry, theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <div className={`flex flex-col items-center justify-center p-6 rounded-lg
                     bg-red-50 border border-red-200`}>
      <AlertCircle size={24} className="text-red-500 mb-2" />
      <p className="text-sm text-red-700 mb-2">Failed to load image</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                     bg-red-100 text-red-700 hover:bg-red-200 transition-colors
                     text-sm font-medium"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * Main InlineImage Component
 */
export function InlineImage({
  src,
  alt,
  caption,
  width,
  height,
  aspectRatio = '16/9',
  maxWidth = '100%',
  lazyLoad = true,
  showLightbox = true,
  theme
}) {
  const themeClasses = theme?.classes || {};
  const [status, setStatus] = useState(ImageStatus.LOADING);
  const [showModal, setShowModal] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const imgRef = useRef(null);

  // Calculate aspect ratio from dimensions if provided
  const computedAspectRatio = width && height
    ? `${width}/${height}`
    : aspectRatio;

  const handleLoad = () => setStatus(ImageStatus.READY);

  const handleError = () => setStatus(ImageStatus.ERROR);

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    setStatus(ImageStatus.LOADING);
  };

  // Force re-render on retry
  const imgSrc = retryCount > 0 ? `${src}?retry=${retryCount}` : src;

  return (
    <>
      <figure
        className={`relative rounded-xl overflow-hidden border
                    ${themeClasses.border || 'border-gray-200'}
                    ${themeClasses.bgSecondary || 'bg-gray-50'}`}
        style={{ maxWidth }}
      >
        {/* Loading state */}
        {status === ImageStatus.LOADING && (
          <ImagePlaceholder aspectRatio={computedAspectRatio} theme={theme} />
        )}

        {/* Error state */}
        {status === ImageStatus.ERROR && (
          <ImageError onRetry={handleRetry} theme={theme} />
        )}

        {/* Image */}
        <div className={`relative ${status !== ImageStatus.READY ? 'hidden' : ''}`}>
          <img
            ref={imgRef}
            src={imgSrc}
            alt={alt || ''}
            loading={lazyLoad ? 'lazy' : 'eager'}
            onLoad={handleLoad}
            onError={handleError}
            className="w-full h-auto object-contain"
            style={{ aspectRatio: computedAspectRatio }}
          />

          {/* Lightbox trigger overlay */}
          {showLightbox && status === ImageStatus.READY && (
            <button
              onClick={() => setShowModal(true)}
              className="absolute inset-0 flex items-center justify-center
                         bg-black/0 hover:bg-black/20 transition-colors group"
            >
              <div className="p-2 rounded-full bg-black/50 opacity-0 group-hover:opacity-100
                             transition-opacity">
                <Maximize2 size={20} className="text-white" />
              </div>
            </button>
          )}
        </div>

        {/* Caption */}
        {caption && status === ImageStatus.READY && (
          <figcaption className={`px-3 py-2 text-sm text-center
                                  ${themeClasses.textMuted || 'text-gray-600'}
                                  ${themeClasses.bgTertiary || 'bg-gray-100'}`}>
            {caption}
          </figcaption>
        )}
      </figure>

      {/* Lightbox Modal */}
      {showModal && (
        <ImageLightbox
          src={src}
          alt={alt}
          caption={caption}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}

/**
 * Image gallery for multiple images
 */
export function ImageGallery({ images, theme, columns = 2 }) {
  const themeClasses = theme?.classes || {};

  if (!images || images.length === 0) return null;

  // Single image - full width
  if (images.length === 1) {
    return (
      <InlineImage
        src={images[0].src}
        alt={images[0].alt}
        caption={images[0].caption}
        theme={theme}
      />
    );
  }

  // Multiple images - grid layout
  return (
    <div className={`grid gap-3 ${columns === 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'}`}>
      {images.map((img, idx) => (
        <InlineImage
          key={img.src || idx}
          src={img.src}
          alt={img.alt}
          caption={img.caption}
          aspectRatio={images.length > 2 ? '1/1' : '16/9'}
          theme={theme}
        />
      ))}
    </div>
  );
}

/**
 * Thumbnail preview with click to expand
 */
export function ImageThumbnail({ src, alt, size = 48, theme, onClick }) {
  const themeClasses = theme?.classes || {};
  const [status, setStatus] = useState(ImageStatus.LOADING);

  return (
    <button
      onClick={onClick}
      className={`relative rounded-lg overflow-hidden flex-shrink-0 border
                  ${themeClasses.border || 'border-gray-200'}
                  hover:opacity-80 transition-opacity`}
      style={{ width: size, height: size }}
    >
      {status === ImageStatus.LOADING && (
        <div className={`absolute inset-0 ${themeClasses.bgSecondary || 'bg-gray-100'} animate-pulse`} />
      )}

      {status === ImageStatus.ERROR && (
        <div className={`absolute inset-0 ${themeClasses.bgSecondary || 'bg-gray-100'}
                         flex items-center justify-center`}>
          <ImageIcon size={16} className={themeClasses.textMuted || 'text-gray-400'} />
        </div>
      )}

      <img
        src={src}
        alt={alt || ''}
        onLoad={() => setStatus(ImageStatus.READY)}
        onError={() => setStatus(ImageStatus.ERROR)}
        className={`w-full h-full object-cover ${status !== ImageStatus.READY ? 'opacity-0' : ''}`}
      />
    </button>
  );
}

export default InlineImage;
