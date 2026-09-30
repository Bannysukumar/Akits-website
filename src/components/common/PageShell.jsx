import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { siteInfo, resolveUrl } from '../../utils/helpers';
import Breadcrumbs from './Breadcrumbs';
import Sidebar from './Sidebar';

export default function PageShell({ page, links = [], sidebarTitle = 'Quick Links', children }) {
  const banner = resolveUrl(page?.banner_image);

  useEffect(() => {
    const college = siteInfo.full_name;
    document.title = page?.title ? `${page.title} | ${siteInfo.site_name}` : college;
    const meta = document.querySelector('meta[name="description"]');
    if (meta && page?.meta_description) meta.content = page.meta_description;
  }, [page]);

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      {banner && (
        <div className="page-banner">
          <img src={banner} alt="" />
        </div>
      )}
      <div className="container page-body">
        <Breadcrumbs crumbs={page?.breadcrumbs} current={page?.route} />
        <div className={links.length ? 'layout-grid' : 'layout-grid single'}>
          <div className="page-main">{children}</div>
          <Sidebar title={sidebarTitle} links={links} />
        </div>
      </div>
    </motion.article>
  );
}
