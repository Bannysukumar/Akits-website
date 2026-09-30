import { Link } from 'react-router-dom';
import { useEffect } from 'react';
import { siteInfo } from '../../utils/helpers';

export default function NotFoundPage() {
  useEffect(() => {
    document.title = `Page not found | ${siteInfo.site_name}`;
  }, []);

  return (
    <div className="container not-found">
      <strong>404</strong>
      <h1>Page not found</h1>
      <p>The page you requested is not available on the {siteInfo.full_name} website.</p>
      <Link className="btn" to="/">Back to Home</Link>
    </div>
  );
}
