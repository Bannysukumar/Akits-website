import fs from 'fs';
import path from 'path';

const manifest = JSON.parse(fs.readFileSync('public/original/manifest.json', 'utf8'));
const shell = JSON.parse(fs.readFileSync('public/original/shell.json', 'utf8'));
const hrefs = [...shell.header.matchAll(/href="(\/[^"#?]*)"/g)].map((match) => match[1].replace(/\/$/, '') || '/');
const nav = JSON.parse(fs.readFileSync('src/data/navigation.json', 'utf8'));
const navRoutes = [];
function walk(items) {
  for (const item of items) {
    if (item.path && item.path !== '#') navRoutes.push(`/${String(item.path).replace(/^\/+|\/+$/g, '')}`);
    if (item.children) walk(item.children);
  }
}
walk(nav);
const wanted = [...new Set([...hrefs, ...navRoutes])].filter((route) => route !== '/' && !manifest[route]);

function clean(html) {
  html = html.replace(/<script[\s\S]*?<\/script>/gi, '');
  html = html.replace(/(\s(?:src|srcset|href))=(["'])\/\//gi, '$1=$2https://');
  html = html.replace(/href=(["'])https?:\/\/akits\.ac\.in\/?([^"'#?]*)([^"']*)\1/gi, (match, quote, pathPart, tail) => {
    if (/\.(pdf|jpe?g|png|gif|webp|svg|css|js|zip|docx?|xlsx?|mp4|xml)$/i.test(pathPart)) return match;
    const route = `/${pathPart.replace(/^\/+|\/+$/g, '')}`;
    return `href=${quote}${route === '/' ? '/' : route}${tail}${quote}`;
  });
  html = html.replace(/action=(["'])https?:\/\/akits\.ac\.in[^"']*\1/gi, 'action=$1#$1');
  html = html.replace(
    /(<div class=['"]marquee-hsas-shortcode-67['"][^>]*>)([\s\S]*?)(<\/div>)/i,
    '$1<div class="akits-marquee-track">$2$2</div>$3',
  );
  return html;
}

const cssDir = 'akits_scraped_resources/stylesheets';
const saved = [];
const failed = [];

for (const route of wanted) {
  const url = `https://akits.ac.in${route}/`;
  try {
    const response = await fetch(url, { redirect: 'follow' });
    if (!response.ok) {
      failed.push(`${route} ${response.status}`);
      continue;
    }
    const html = await response.text();
    let start = html.indexOf('<div data-elementor-type="wp-page"');
    let end = start >= 0 ? html.indexOf('</main>', start) : -1;
    if (start < 0 || end < 0) {
      start = html.indexOf('<main id="main"');
      const openEnd = html.indexOf('>', start);
      end = html.indexOf('</main>', openEnd);
      start = openEnd + 1;
    }
    if (start < 0 || end < 0 || end - start < 80) {
      failed.push(`${route} no-content`);
      continue;
    }
    const chunk = clean(html.slice(start, end));
    const id = (chunk.match(/data-elementor-id="(\d+)"/) || html.match(/elementor-post-(\d+)-css/) || [])[1] || '';
    if (id) {
      const cssName = `post-${id}.css`;
      const cssPath = path.join(cssDir, cssName);
      if (!fs.existsSync(cssPath)) {
        const cssRes = await fetch(`https://akits.ac.in/wp-content/uploads/elementor/css/${cssName}`);
        if (cssRes.ok) {
          const css = await cssRes.text();
          if (css.includes('{')) fs.writeFileSync(cssPath, css);
        }
      }
    }
    const rel = `${route.slice(1)}.html`;
    const dest = path.join('public/original', rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, chunk);
    manifest[route] = { id, css: id ? `post-${id}.css` : '', file: `/${rel.replace(/\\/g, '/')}` };
    saved.push(route);
    console.log('saved', route, id || 'no-id');
  } catch (error) {
    failed.push(`${route} ${error.message}`);
  }
}

fs.writeFileSync('public/original/manifest.json', JSON.stringify(manifest, null, 2));
console.log('\nSAVED', saved.length);
console.log('FAILED', failed.length);
console.log(failed.join('\n'));
