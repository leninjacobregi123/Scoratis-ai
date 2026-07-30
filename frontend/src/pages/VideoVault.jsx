import { useOutletContext } from 'react-router-dom';
import { PlayCircle, Video, Film, Loader } from 'lucide-react';

const VideoVault = () => {
  const { videos, loading } = useOutletContext();

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="flex items-center gap-4 mb-8">
        <Film className="w-8 h-8 text-primary" />
        <h1 className="text-3xl font-bold text-text-primary">Video Vault</h1>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-16">
          <Video className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-secondary">No Videos Yet</h2>
          <p className="text-text-tertiary">Your generated videos will appear here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {videos.filter(video => video && video.path).map((video) => (
            <div key={video.id} className="bg-bg-secondary rounded-lg shadow-md overflow-hidden group">
              <a href={video.path} target="_blank" rel="noreferrer" className="block relative">
                <img
                  src={video.path.replace('.mp4', '.jpg')}
                  alt={video.topic || 'Video'}
                  className="w-full h-48 object-cover"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
                <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <PlayCircle className="w-16 h-16 text-white" />
                </div>
              </a>
              <div className="p-4">
                <h3 className="font-semibold text-text-primary truncate">{video.topic || 'Untitled Video'}</h3>
                <p className="text-sm text-text-tertiary">{video.created_at ? new Date(video.created_at).toLocaleString() : 'Unknown date'}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default VideoVault;