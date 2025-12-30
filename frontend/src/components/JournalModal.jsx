import { useState, useEffect } from 'react'
import { X, Save, Edit3 } from 'lucide-react'

export default function JournalModal({ journal, folders, onSave, onClose }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [tags, setTags] = useState('')
  const [folderId, setFolderId] = useState('')

  useEffect(() => {
    if (journal) {
      setTitle(journal.title || '')
      setContent(journal.content || '')
      setTags(journal.tags?.join(', ') || '')
      setFolderId(journal.folder_id || '')
    }
  }, [journal])

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave({
      title: title.trim(),
      content: content.trim(),
      tags: tags.split(',').map(t => t.trim()).filter(t => t),
      folder_id: folderId || null
    })
  }

  return (
    <div className="fixed inset-0 modal-backdrop flex items-center justify-center z-50">
      <div className="modal-content w-full max-w-4xl mx-4 corner-decoration">
        <div className="p-6 border-b border-border-color flex justify-between items-center">
          <h3 className="text-2xl font-light text-text-primary flex items-center space-x-3" style={{ fontFamily: 'Georgia, serif' }}>
            <div className="w-10 h-10 rounded-xl bg-accent-olive/20 flex items-center justify-center">
              <Edit3 className="w-5 h-5 text-accent-olive" />
            </div>
            <span>{journal?.id ? 'Edit Journal' : 'Create New Journal'}</span>
          </h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-text-secondary text-sm font-medium mb-2">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
                placeholder="Enter your journal title"
                required
              />
            </div>
            <div>
              <label className="block text-text-secondary text-sm font-medium mb-2">Folder</label>
              <select
                value={folderId}
                onChange={(e) => setFolderId(e.target.value)}
                className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
              >
                <option value="">No folder</option>
                {folders.map(folder => (
                  <option key={folder.id} value={folder.id}>{folder.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-text-secondary text-sm font-medium mb-2">Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-accent-olive transition-colors resize-none"
              placeholder="What's on your mind today?"
              required
            />
          </div>

          <div>
            <label className="block text-text-secondary text-sm font-medium mb-2">Tags</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
              placeholder="Add tags separated by commas"
            />
          </div>

          <div className="flex justify-end space-x-4 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex items-center space-x-2">
              <Save className="w-4 h-4" />
              <span>Save Journal</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
