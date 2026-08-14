import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { PlayCircle, Video, Film, Loader } from 'lucide-react';

// Card thumbnail. The render pipeline (tasks/video_tasks.py) only ever writes
// the .mp4 - it never produces a companion .jpg - so the derived thumbnail URL
// 404s for every locally generated video. The previous version hid the <img>
// on error, which left the anchor with no in-flow child (the hover overlay is
// absolutely positioned) and collapsed the whole card to zero height. Render a
// placeholder that occupies the same space instead of removing the element.
function VideoThumbnail({ video }) {
  const [failed, setFailed] = useState(false);
  const thumbSrc = video.path?.replace(/\.mp4$/i, '.jpg');
  const showPlaceholder = failed || !thumbSrc;

  return (
    <a
      href={video.path}
      target="_blank"
      rel="noreferrer"
      className="block relative h-48 bg-bg-tertiary"
    >
      {showPlaceholder ? (
        <div className="w-full h-full flex items-center justify-center">
          <Film className="w-12 h-12 text-text-muted" />
        </div>
      ) : (
        <img
          src={thumbSrc}
          alt={video.topic || 'Video'}
          className="w-full h-full object-cover"
          onError={() => setFailed(true)}
        />
      )}
      <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <PlayCircle className="w-16 h-16 text-white" />
      </div>
    </a>
  );
}

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
              <VideoThumbnail video={video} />
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