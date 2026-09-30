import fs from 'fs';

const manifest = JSON.parse(fs.readFileSync('public/original/manifest.json', 'utf8'));
const site = 'https://akits-ac-in.vercel.app';
const featured = new Set(['/about-us', '/admissions', '/contact-us', '/administration']);
const paths = Object.keys(manifest)
  .filter((path) => path && path !== '/#')
  .sort((a, b) => (a === '/' ? -1 : b === '/' ? 1 : a.localeCompare(b)));

const urls = paths
  .map((path) => {
    const loc = path === '/' ? `${site}/` : `${site}${path}`;
    const priority = path === '/' ? '1.0' : featured.has(path) ? '0.9' : '0.7';
    return `  <url>
    <loc>${loc}</loc>
    <lastmod>2026-09-30</lastmod>
    <changefreq>weekly</changefreq>
    <priority>${priority}</priority>
  </url>`;
  })
  .join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

fs.writeFileSync('public/sitemap.xml', xml);
console.log('urls', paths.length);
