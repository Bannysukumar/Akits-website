import { useEffect, useState } from 'react';
import { FaTimes, FaChevronLeft, FaChevronRight } from 'react-icons/fa';
import { decodeHtml, resolveUrl } from '../../utils/helpers';

export default function ImageGallery({ images = [] }) {
  const [active, setActive] = useState(-1);
  const slides = images
    .map((image) => ({ src: resolveUrl(image.src), alt: decodeHtml(image.alt) }))
    .filter((image) => image.src);

  useEffect(() => {
    if (active < 0) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') setActive(-1);
      if (event.key === 'ArrowRight') setActive((index) => (index + 1) % slides.length);
      if (event.key === 'ArrowLeft') setActive((index) => (index - 1 + slides.length) % slides.length);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, slides.length]);

  if (!slides.length) return null;

  return (
    <>
      <div className="gallery-grid">
        {slides.map((image, index) => (
          <button type="button" className="gallery-card" key={`${image.src}-${index}`} onClick={() => setActive(index)}>
            <img src={image.src} alt={image.alt || 'Gallery image'} loading="lazy" />
            {image.alt && <span>{image.alt}</span>}
          </button>
        ))}
      </div>
      {active >= 0 && (
        <div className="lightbox" role="dialog" aria-modal="true" onClick={() => setActive(-1)}>
          <button type="button" className="lightbox-close" aria-label="Close" onClick={() => setActive(-1)}>
            <FaTimes />
          </button>
          {slides.length > 1 && (
            <button
              type="button"
              className="lightbox-nav prev"
              aria-label="Previous image"
              onClick={(event) => {
                event.stopPropagation();
                setActive((index) => (index - 1 + slides.length) % slides.length);
              }}
            >
              <FaChevronLeft />
            </button>
          )}
          <img src={slides[active].src} alt={slides[active].alt || ''} onClick={(event) => event.stopPropagation()} />
          {slides.length > 1 && (
            <button
              type="button"
              className="lightbox-nav next"
              aria-label="Next image"
              onClick={(event) => {
                event.stopPropagation();
                setActive((index) => (index + 1) % slides.length);
              }}
            >
              <FaChevronRight />
            </button>
          )}
        </div>
      )}
    </>
  );
}
