import { useState, useRef } from 'react';
import { Paperclip, X, File, FileText, Image, Upload, Loader2, Check, AlertCircle } from 'lucide-react';

// Allowed file types for upload
const ALLOWED_TYPES = {
  'application/pdf': { icon: FileText, label: 'PDF' },
  'text/plain': { icon: FileText, label: 'TXT' },
  'text/markdown': { icon: FileText, label: 'MD' },
  'text/html': { icon: FileText, label: 'HTML' },
  'application/msword': { icon: FileText, label: 'DOC' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: FileText, label: 'DOCX' },
  'image/png': { icon: Image, label: 'PNG' },
  'image/jpeg': { icon: Image, label: 'JPG' },
  'image/gif': { icon: Image, label: 'GIF' },
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// Attachment Button - triggers file picker
export function AttachmentButton({ onFileSelect, disabled = false, className = '' }) {
  const fileInputRef = useRef(null);

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!ALLOWED_TYPES[file.type]) {
        alert('Unsupported file type. Please upload PDF, DOC, DOCX, TXT, MD, HTML, or image files.');
        return;
      }

      // Validate file size
      if (file.size > MAX_FILE_SIZE) {
        alert('File is too large. Maximum size is 10MB.');
        return;
      }

      onFileSelect(file);
    }
    // Reset input so the same file can be selected again
    e.target.value = '';
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        className={`p-2 rounded-lg transition-all hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-gray-500 hover:text-gray-700 ${className}`}
        title="Attach file"
      >
        <Paperclip className="w-5 h-5" />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt,.md,.html,.png,.jpg,.jpeg,.gif"
        onChange={handleFileChange}
        className="hidden"
      />
    </>
  );
}

// Attachment Preview - shows file details before sending
export function AttachmentPreview({ file, uploadProgress, uploadStatus, onRemove }) {
  const fileType = ALLOWED_TYPES[file.type] || { icon: File, label: 'FILE' };
  const FileIcon = fileType.icon;
  const fileSizeKB = (file.size / 1024).toFixed(1);
  const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
  const displaySize = file.size > 1024 * 1024 ? `${fileSizeMB} MB` : `${fileSizeKB} KB`;

  // Status colors
  const statusColors = {
    pending: 'bg-gray-100 border-gray-200',
    uploading: 'bg-blue-50 border-blue-200',
    processing: 'bg-amber-50 border-amber-200',
    completed: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
  };

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg border ${statusColors[uploadStatus] || statusColors.pending} transition-all`}>
      {/* File icon */}
      <div className="flex-shrink-0 w-10 h-10 bg-white rounded-lg border flex items-center justify-center">
        <FileIcon className="w-5 h-5 text-gray-600" />
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>{fileType.label}</span>
          <span>·</span>
          <span>{displaySize}</span>
          {uploadStatus === 'uploading' && uploadProgress > 0 && (
            <>
              <span>·</span>
              <span>{uploadProgress}%</span>
            </>
          )}
        </div>
      </div>

      {/* Status indicator */}
      <div className="flex-shrink-0">
        {uploadStatus === 'uploading' && (
          <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
        )}
        {uploadStatus === 'processing' && (
          <div className="flex items-center gap-1 text-amber-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-xs">Processing</span>
          </div>
        )}
        {uploadStatus === 'completed' && (
          <Check className="w-5 h-5 text-green-500" />
        )}
        {uploadStatus === 'error' && (
          <AlertCircle className="w-5 h-5 text-red-500" />
        )}
        {(uploadStatus === 'pending' || !uploadStatus) && (
          <button
            onClick={onRemove}
            className="p-1 hover:bg-gray-200 rounded transition-colors"
            title="Remove file"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        )}
      </div>
    </div>
  );
}

// Attached Documents List - shows documents attached to current message
export function AttachedDocsList({ documents = [], onViewDocument, onRemoveDocument }) {
  if (!documents.length) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-full text-sm"
        >
          <FileText className="w-3.5 h-3.5 text-blue-600" />
          <span
            className="text-blue-700 cursor-pointer hover:underline max-w-[150px] truncate"
            onClick={() => onViewDocument?.(doc)}
            title={doc.title}
          >
            {doc.title}
          </span>
          <button
            onClick={() => onRemoveDocument?.(doc.id)}
            className="p-0.5 hover:bg-blue-100 rounded-full transition-colors"
            title="Remove"
          >
            <X className="w-3 h-3 text-blue-500" />
          </button>
        </div>
      ))}
    </div>
  );
}

// Upload Progress Overlay - full-screen upload indicator
export function UploadProgressOverlay({ isVisible, fileName, progress, stage }) {
  if (!isVisible) return null;

  const stages = {
    uploading: { label: 'Uploading...', color: 'bg-blue-500' },
    processing: { label: 'Processing document...', color: 'bg-amber-500' },
    embedding: { label: 'Creating embeddings...', color: 'bg-purple-500' },
    completed: { label: 'Complete!', color: 'bg-green-500' },
  };

  const currentStage = stages[stage] || stages.uploading;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <Upload className="w-8 h-8 text-gray-600 animate-bounce" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {currentStage.label}
          </h3>
          <p className="text-sm text-gray-500 mb-4 truncate px-4">
            {fileName}
          </p>

          {/* Progress bar */}
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${currentStage.color} transition-all duration-300 ease-out`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-gray-400">{progress}%</p>
        </div>
      </div>
    </div>
  );
}

// Document Pill - small indicator for uploaded documents in chat
export function DocumentPill({ document, onClick }) {
  return (
    <button
      onClick={() => onClick?.(document)}
      className="inline-flex items-center gap-1.5 px-2 py-1 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md text-xs text-blue-700 transition-colors"
    >
      <FileText className="w-3 h-3" />
      <span className="max-w-[100px] truncate">{document.title}</span>
    </button>
  );
}

export default {
  AttachmentButton,
  AttachmentPreview,
  AttachedDocsList,
  UploadProgressOverlay,
  DocumentPill,
};
