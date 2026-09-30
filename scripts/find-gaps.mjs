import fs from 'fs';

const nav = JSON.parse(fs.readFileSync('src/data/navigation.json', 'utf8'));
const manifest = JSON.parse(fs.readFileSync('public/original/manifest.json', 'utf8'));
const routes = [];

function walk(items) {
  for (const item of items) {
    if (item.path) routes.push(`/${String(item.path).replace(/^\/+|\/+$/g, '')}`);
    if (item.children) walk(item.children);
  }
}
walk(nav);

const missing = [...new Set(routes)].filter((route) => route !== '/' && !manifest[route]);
console.log('MISSING ROUTES', missing.length);
console.log(missing.join('\n'));

const imageIssues = [];
for (const [route, info] of Object.entries(manifest)) {
  const file = `public/original${info.file}`;
  if (!fs.existsSync(file)) {
    imageIssues.push(`${route} MISSING FILE`);
    continue;
  }
  const html = fs.readFileSync(file, 'utf8');
  const imgs = [...html.matchAll(/<img\b[^>]*>/gi)].map((match) => match[0]);
  const bad = imgs.filter((tag) => {
    const src = (tag.match(/\ssrc=["']([^"']*)["']/i) || [])[1] || '';
    return !src || src.startsWith('data:') && src.length < 40 || /placeholder|blank\.gif|1x1/.test(src);
  });
  const lazy = imgs.filter((tag) => /data-src=|data-lazy/.test(tag) && !/\ssrc=["']https?:/.test(tag));
  if (bad.length || lazy.length) imageIssues.push(`${route} bad=${bad.length} lazy=${lazy.length}`);
}
console.log('\nIMAGE ISSUES', imageIssues.length);
console.log(imageIssues.join('\n'));
