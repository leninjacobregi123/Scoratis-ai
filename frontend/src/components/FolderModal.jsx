import { useState } from 'react'
import { X, FolderPlus } from 'lucide-react'

const colors = [
  { value: '#d4af37', from: 'from-amber-400', to: 'to-amber-600' },
  { value: '#ffffff', from: 'from-white', to: 'to-gray-200' },
  { value: '#888888', from: 'from-gray-400', to: 'to-gray-600' },
  { value: '#2a2a2a', from: 'from-gray-700', to: 'to-gray-900' },
  { value: '#a08020', from: 'from-yellow-600', to: 'to-yellow-800' },
  { value: '#4a4a4a', from: 'from-gray-500', to: 'to-gray-700' },
]

export default function FolderModal({ onSave, onClose }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState('#d4af37')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave({
      name: name.trim(),
      description: description.trim(),
      color
    })
  }

  return (
    <div className="fixed inset-0 modal-backdrop flex items-center justify-center z-50">
      <div className="modal-content w-full max-w-lg mx-4 corner-decoration">
        <div className="p-6 border-b border-border-color flex justify-between items-center">
          <h3 className="text-xl font-light text-text-primary flex items-center space-x-3" style={{ fontFamily: 'Georgia, serif' }}>
            <div className="w-10 h-10 rounded-xl bg-accent-olive/20 flex items-center justify-center">
              <FolderPlus className="w-5 h-5 text-accent-olive" />
            </div>
            <span>Create New Folder</span>
          </h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-text-secondary text-sm font-medium mb-2">Folder Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
              placeholder="Enter folder name"
              required
            />
          </div>

          <div>
            <label className="block text-text-secondary text-sm font-medium mb-2">Description (Optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full bg-bg-card border border-border-color rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-accent-olive transition-colors resize-none"
              placeholder="What will you store in this folder?"
            />
          </div>

          <div>
            <label className="block text-text-secondary text-sm font-medium mb-2">Color</label>
            <div className="flex space-x-3">
              {colors.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setColor(c.value)}
                  className={`w-10 h-10 rounded-xl bg-gradient-to-br ${c.from} ${c.to} border-2 transition-transform hover:scale-110 ${
                    color === c.value ? 'border-white' : 'border-transparent'
                  }`}
                />
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-4 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex items-center space-x-2">
              <FolderPlus className="w-4 h-4" />
              <span>Create Folder</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
