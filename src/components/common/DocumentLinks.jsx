import { FaDownload, FaFilePdf } from 'react-icons/fa';
import { decodeHtml, resolveUrl } from '../../utils/helpers';

export default function DocumentLinks({ documents = [] }) {
  const items = documents.filter((doc) => doc.url);
  if (!items.length) return null;
  return (
    <div className="doc-list">
      {items.map((doc, index) => (
        <a key={`${doc.url}-${index}`} className="doc-link" href={resolveUrl(doc.url)} target="_blank" rel="noreferrer">
          <FaFilePdf size={18} />
          <span>{decodeHtml(doc.text) || doc.type || 'Download'}</span>
          <FaDownload size={14} />
        </a>
      ))}
    </div>
  );
}
