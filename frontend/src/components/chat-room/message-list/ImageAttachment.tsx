import { useState, memo } from 'react';

interface ImageAttachmentProps {
  imageData: string;
  imageMediaType: string;
  isUserMessage: boolean;
}

export const ImageAttachment = memo(({ imageData, imageMediaType, isUserMessage }: ImageAttachmentProps) => {
  const [showLightbox, setShowLightbox] = useState(false);

  return (
    <>
      <div className={`mb-2 ${isUserMessage ? 'flex justify-end' : ''}`}>
        <img
          src={`data:${imageMediaType};base64,${imageData}`}
          alt="Attached"
          className="max-w-xs max-h-64 rounded-xl border border-slate-200 shadow-sm cursor-pointer hover:opacity-90 transition-opacity"
          loading="lazy"
          onClick={() => setShowLightbox(true)}
          title="Click to view full size"
        />
      </div>

      {/* Lightbox Modal */}
      {showLightbox && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setShowLightbox(false)}
        >
          <button
            className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors"
            onClick={() => setShowLightbox(false)}
            aria-label="Close lightbox"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <img
            src={`data:${imageMediaType};base64,${imageData}`}
            alt="Full size"
            className="max-w-full max-h-full object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
});
