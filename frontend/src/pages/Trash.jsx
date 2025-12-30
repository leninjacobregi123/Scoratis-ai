import { useState, useEffect } from 'react'
import { Trash2, RotateCcw, AlertTriangle } from 'lucide-react'
import { useApi } from '../hooks/useApi'

export default function Trash() {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const api = useApi()

  useEffect(() => {
    loadTrash()
  }, [])

  const loadTrash = async () => {
    try {
      const data = await api.get('/chat/trash')
      setConversations(data.conversations || [])
    } catch (error) {
      console.error('Failed to load trash:', error)
    } finally {
      setLoading(false)
    }
  }

  const restoreConversation = async (id) => {
    try {
      await api.post(`/chat/conversation/${id}/restore`)
      loadTrash()
    } catch (error) {
      console.error('Failed to restore:', error)
    }
  }

  const emptyTrash = async () => {
    if (!confirm('Permanently delete all conversations in trash?')) return
    try {
      await api.post('/chat/trash/empty')
      setConversations([])
    } catch (error) {
      console.error('Failed to empty trash:', error)
    }
  }

  return (
    <div className="h-full overflow-y-auto relative z-10 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-accent-olive/20 flex items-center justify-center">
              <Trash2 className="w-6 h-6 text-accent-olive" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Trash</h1>
              <p className="text-text-secondary">Deleted items are kept for 30 days</p>
            </div>
          </div>
          {conversations.length > 0 && (
            <button
              onClick={emptyTrash}
              className="px-4 py-2 bg-red-500/20 border border-red-500/50 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
            >
              Empty Trash
            </button>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex space-x-1">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce" />
              <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-bg-card/50 flex items-center justify-center">
              <Trash2 className="w-12 h-12 text-text-muted" />
            </div>
            <h3 className="text-xl font-semibold text-text-primary mb-2" style={{ fontFamily: 'Georgia, serif' }}>Trash is empty</h3>
            <p className="text-text-muted">Deleted conversations will appear here</p>
          </div>
        ) : (
          <div className="space-y-4">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className="glass-card rounded-xl p-4 flex items-center justify-between"
              >
                <div>
                  <h3 className="text-text-primary font-medium">{conv.title || 'Untitled conversation'}</h3>
                  <p className="text-sm text-text-muted">
                    Deleted {new Date(conv.deleted_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => restoreConversation(conv.id)}
                  className="flex items-center space-x-2 px-3 py-2 bg-accent-olive/20 text-accent-olive rounded-lg hover:bg-accent-olive/30 transition-colors"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Restore</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
