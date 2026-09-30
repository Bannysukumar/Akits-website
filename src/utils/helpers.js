import siteInfo from '../data/site_info.json';
import navigation from '../data/navigation.json';
import pages from '../data/pages.json';
import routes from '../data/routes.json';
import footerInfo from '../data/footer.json';

export { siteInfo, navigation, pages, routes, footerInfo };

export function decodeHtml(value) {
  if (value == null) return '';
  return String(value)
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#039;|&apos;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function resolveUrl(src) {
  if (!src || typeof src !== 'string') return '';
  if (src.startsWith('data:')) return src;
  if (src.startsWith('//')) return `https:${src}`;
  return src;
}

export function toRoute(path) {
  if (!path || path === '#') return null;
  const clean = String(path).replace(/^\/+|\/+$/g, '');
  if (!clean) return '/';
  return `/${clean}`;
}

export function normalizePath(pathname) {
  if (!pathname) return '/';
  const path = pathname.split('?')[0].split('#')[0].replace(/\/+$/, '');
  return path || '/';
}

const pageMap = new Map(pages.map((page) => [page.route, page]));
const routeMeta = new Map(routes.map((route) => [route.route, route]));

export function getPage(pathname) {
  const path = normalizePath(pathname);
  const page = pageMap.get(path);
  if (!page) return null;
  const meta = routeMeta.get(path);
  if (!page.meta_description && meta?.description) {
    return { ...page, meta_description: meta.description };
  }
  return page;
}

export function flattenNav(items = navigation, acc = []) {
  for (const item of items) {
    const route = toRoute(item.path);
    if (route) acc.push({ label: decodeHtml(item.label), route, href: item.href });
    if (item.children?.length) flattenNav(item.children, acc);
  }
  return acc;
}

export const navLinks = flattenNav();

export function findNavTrail(pathname, items = navigation, trail = []) {
  const target = normalizePath(pathname);
  for (const item of items) {
    const route = toRoute(item.path);
    const next = [...trail, item];
    if (route === target) return next;
    if (item.children?.length) {
      const found = findNavTrail(target, item.children, next);
      if (found) return found;
    }
  }
  return null;
}

export function getSidebarLinks(pathname) {
  const trail = findNavTrail(pathname);
  if (!trail || trail.length < 2) return [];
  const parent = trail[trail.length - 2];
  if (!parent.children?.length) return [];
  return parent.children
    .map((child) => ({ label: decodeHtml(child.label), route: toRoute(child.path) }))
    .filter((child) => child.route);
}

export function isDepartmentPath(pathname) {
  const trail = findNavTrail(pathname);
  if (trail && trail.length >= 3 && trail.some((node) => node.label === 'Departments')) {
    return true;
  }
  const slug = normalizePath(pathname).replace(/^\//, '');
  return siteInfo.departments.some((dept) => dept.pages?.includes(slug));
}

export function isGalleryPath(pathname) {
  const path = normalizePath(pathname);
  const trail = findNavTrail(path);
  const label = trail?.[trail.length - 1]?.label || '';
  if (/photo gallery|media gallery|video gallery|academic photos|non-academics photos|placement photos/i.test(label)) {
    return true;
  }
  return /\/gallery\/|academic-photos|non-academics-photos|placement-photos/.test(path);
}

export function isHodPath(pathname) {
  return /hod/i.test(normalizePath(pathname));
}

export function accreditationBadges(list = siteInfo.accreditations) {
  const found = {};
  for (const item of list) {
    const text = item.toLowerCase();
    if (text.includes('naac')) {
      const grade = item.match(/NAAC\s+([A-C]\+{0,2})/i);
      found.NAAC = grade ? `NAAC ${grade[1].toUpperCase()}` : 'NAAC';
    } else if (text.includes('autonomous')) found.AUTONOMOUS = 'AUTONOMOUS';
    else if (text.includes('aicte')) found.AICTE = 'AICTE';
    else if (text.includes('jntu')) found.JNTU = 'JNTU';
    else if (text.includes('iso')) found.ISO = 'ISO';
  }
  return ['AUTONOMOUS', 'NAAC', 'AICTE', 'JNTU', 'ISO'].map((key) => found[key]).filter(Boolean);
}

export function contentImages(page) {
  if (!page?.images?.length) return [];
  const banner = resolveUrl(page.banner_image);
  return page.images.filter((image) => {
    const src = resolveUrl(image.src);
    if (!src || src.startsWith('data:')) return false;
    if (banner && src === banner) return false;
    const alt = (image.alt || '').toLowerCase();
    if (alt.includes('arrow')) return false;
    const width = Number(image.width);
    const height = Number(image.height);
    if (width && height && width <= 48 && height <= 48) return false;
    return true;
  });
}

export function heroSlides(page, limit = 8) {
  const seen = new Set();
  const slides = [];
  for (const image of page?.images || []) {
    const src = resolveUrl(image.src);
    if (!src || src.startsWith('data:') || seen.has(src)) continue;
    if ((image.alt || '').toLowerCase().includes('arrow')) continue;
    seen.add(src);
    slides.push({ src, alt: image.alt || siteInfo.full_name });
    if (slides.length >= limit) break;
  }
  return slides;
}

export function crumbPath(crumb) {
  const name = decodeHtml(crumb?.name || '');
  if (!crumb?.url || name.toLowerCase() === 'home') return name.toLowerCase() === 'home' ? '/' : null;
  try {
    const raw = crumb.url.startsWith('//') ? `https:${crumb.url}` : crumb.url;
    const url = new URL(raw);
    if (url.hostname.includes('akits.ac.in')) {
      return normalizePath(url.pathname);
    }
  } catch {
    return null;
  }
  return null;
}

export function quickLinksHeading(page) {
  const heading = page?.headings?.find((item) => /quick links/i.test(item.text || ''));
  return heading ? decodeHtml(heading.text) : 'Quick Links';
}

export function isNavMirrorList(list, sidebarLinks) {
  if (!list?.items?.length) return false;
  const items = list.items.map((item) => decodeHtml(item).toLowerCase());
  const short = items.every((item) => item.length < 48);
  const keywordHits = items.filter((item) => /hod|faculty|lab|vision|mission|achiev|about/.test(item)).length;
  if (short && items.length <= 8 && keywordHits >= 4) return true;
  if (!sidebarLinks?.length) return false;
  const labels = sidebarLinks.map((link) => link.label.toLowerCase());
  const hits = items.filter((text) => labels.some((label) => label === text || label.includes(text) || text.includes(label)));
  return hits.length >= Math.min(3, items.length);
}

export function visibleHeadings(page) {
  const title = decodeHtml(page?.title || '').toLowerCase();
  return (page?.headings || [])
    .map((heading) => ({ ...heading, text: decodeHtml(heading.text) }))
    .filter((heading) => heading.text && !/quick links/i.test(heading.text))
    .filter((heading) => heading.text.toLowerCase() !== title);
}

export function childLinks(parentLabel) {
  const parent = navigation.find((item) => item.label === parentLabel);
  if (!parent?.children) return [];
  const links = [];
  const walk = (items) => {
    for (const item of items) {
      const route = toRoute(item.path);
      if (route) links.push({ label: decodeHtml(item.label), route });
      else if (item.children?.length) walk(item.children);
    }
  };
  walk(parent.children);
  return links;
}

export function buildPhotoGalleryPage() {
  const navItem = navLinks.find((link) => link.route === '/gallery/photo-gallery');
  const sources = navLinks
    .map((link) => link.route)
    .filter((route) => /academic-photos|non-academics-photos|placement-photos|media-gallery|alumni-pics/.test(route));
  const images = [];
  const seen = new Set();
  for (const route of sources) {
    const page = pageMap.get(route);
    for (const image of contentImages(page)) {
      const src = resolveUrl(image.src);
      if (!src || seen.has(src)) continue;
      seen.add(src);
      images.push(image);
    }
  }
  return {
    route: '/gallery/photo-gallery',
    title: navItem?.label || 'Photo Gallery',
    meta_description: '',
    breadcrumbs: [
      { name: 'Home', url: 'https://akits.ac.in/' },
      { name: 'Gallery', url: '' },
      { name: navItem?.label || 'Photo Gallery', url: '' },
    ],
    banner_image: pageMap.get('/gallery/media-gallery')?.banner_image || '',
    headings: [],
    paragraphs: [],
    images,
    videos: [],
    iframes: [],
    tables: [],
    lists: [],
    documents: [],
  };
}

export function syntheticPage(pathname) {
  const trail = findNavTrail(pathname);
  if (!trail) return null;
  const item = trail[trail.length - 1];
  const crumbs = [
    { name: 'Home', url: 'https://akits.ac.in/' },
    ...trail.map((node) => ({ name: node.label, url: '' })),
  ];
  return {
    route: normalizePath(pathname),
    title: decodeHtml(item.label),
    meta_description: '',
    breadcrumbs: crumbs,
    banner_image: '',
    headings: [],
    paragraphs: [],
    images: [],
    videos: [],
    iframes: [],
    tables: [],
    lists: [],
    documents: [],
    external_url: item.href && item.href !== '#' ? item.href : '',
  };
}

export function searchPages(query) {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];
  const results = [];
  const seen = new Set();
  for (const page of pages) {
    const title = decodeHtml(page.title);
    const haystack = `${title} ${page.route}`.toLowerCase();
    if (!haystack.includes(q) || seen.has(page.route)) continue;
    seen.add(page.route);
    results.push({ title, route: page.route });
    if (results.length >= 10) break;
  }
  if (results.length < 10) {
    for (const link of navLinks) {
      if (seen.has(link.route)) continue;
      if (!link.label.toLowerCase().includes(q)) continue;
      seen.add(link.route);
      results.push(link);
      if (results.length >= 10) break;
    }
  }
  return results;
}

export function matchDocument(label, documents = []) {
  const text = decodeHtml(label).toLowerCase();
  return documents.find((doc) => {
    const name = decodeHtml(doc.text).toLowerCase();
    return name && (name === text || text.includes(name) || name.includes(text));
  });
}

export function matchInternalRoute(label) {
  const text = decodeHtml(label).toLowerCase();
  if (text.includes('exam')) return navLinks.find((link) => /exam notification/i.test(link.label))?.route;
  if (text.includes('contact') && text.includes('admission')) {
    return navLinks.find((link) => link.route === '/contact-form-for-admissions')?.route
      || navLinks.find((link) => link.route === '/admissions')?.route;
  }
  if (text.includes('admission')) return navLinks.find((link) => link.route === '/admissions')?.route;
  if (text.includes('free') && text.includes('hostel')) return '/free-hostel';
  if (text.includes('hostel')) return navLinks.find((link) => /hostel/i.test(link.label))?.route || '/free-hostel';
  if (text.includes('video') || text.includes('vedio')) return navLinks.find((link) => /video gallery/i.test(link.label))?.route;
  if (text.includes('feedback')) return navLinks.find((link) => /feedback/i.test(link.label))?.route || null;
  return null;
}
