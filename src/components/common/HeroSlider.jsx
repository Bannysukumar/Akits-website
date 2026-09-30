import { useEffect, useState } from 'react';
import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';

export default function HeroSlider({ slides = [] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused || slides.length < 2) return undefined;
    const timer = setInterval(() => {
      setIndex((current) => (current + 1) % slides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [paused, slides.length]);

  if (!slides.length) return null;
  const slide = slides[index];

  return (
    <section
      className="hero"
      aria-label="Campus highlights"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <img src={slide.src} alt={slide.alt || ''} />
      {slides.length > 1 && (
        <>
          <button
            type="button"
            className="hero-btn prev"
            aria-label="Previous slide"
            onClick={() => setIndex((current) => (current - 1 + slides.length) % slides.length)}
          >
            <FaChevronLeft />
          </button>
          <button
            type="button"
            className="hero-btn next"
            aria-label="Next slide"
            onClick={() => setIndex((current) => (current + 1) % slides.length)}
          >
            <FaChevronRight />
          </button>
          <div className="hero-dots">
            {slides.map((item, dotIndex) => (
              <button
                key={item.src}
                type="button"
                className={dotIndex === index ? 'on' : ''}
                aria-label={`Go to slide ${dotIndex + 1}`}
                onClick={() => setIndex(dotIndex)}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
