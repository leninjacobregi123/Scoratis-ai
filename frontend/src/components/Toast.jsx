import { CheckCircle, AlertCircle } from 'lucide-react'

export default function Toast({ message, type = 'success' }) {
  return (
    <div className={`toast show ${type}`}>
      <div className="flex items-center space-x-2">
        {type === 'success' ? (
          <CheckCircle className="w-5 h-5" />
        ) : (
          <AlertCircle className="w-5 h-5" />
        )}
        <span className="font-medium">{message}</span>
      </div>
    </div>
  )
}
