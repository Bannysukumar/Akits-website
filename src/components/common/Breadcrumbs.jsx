import { Link } from 'react-router-dom';
import { crumbPath, decodeHtml, normalizePath } from '../../utils/helpers';

export default function Breadcrumbs({ crumbs = [], current = '' }) {
  if (!crumbs.length) return null;
  const path = normalizePath(current);

  return (
    <ol className="crumbs">
      {crumbs.map((crumb, index) => {
        const label = decodeHtml(crumb.name);
        const href = crumbPath(crumb);
        const isLast = index === crumbs.length - 1;
        return (
          <li key={`${label}-${index}`}>
            {!isLast && href && href !== path ? <Link to={href}>{label}</Link> : <span>{label}</span>}
          </li>
        );
      })}
    </ol>
  );
}
