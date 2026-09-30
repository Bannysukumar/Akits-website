export default function AnnouncementTicker({ items = [] }) {
  if (!items.length) return null;
  const loop = [...items, ...items];

  return (
    <div className="ticker" aria-label="Announcements">
      <div className="ticker-track">
        {loop.map((item, index) => (
          <span className="ticker-item" key={`${item}-${index}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
