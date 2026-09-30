import fs from 'fs';
import path from 'path';

const root = process.cwd();
const source = path.join(root, 'akits_pages_source');
const outDir = path.join(root, 'public', 'original');
const cssDir = path.join(root, 'akits_scraped_resources', 'stylesheets');

function walk(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, acc);
    else if (entry.name === 'index.html') acc.push(full);
  }
  return acc;
}

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

function routeFromFile(file) {
  const rel = path.relative(source, path.dirname(file)).replace(/\\/g, '/');
  if (!rel || rel === '.') return '/';
  return `/${rel}`;
}

fs.mkdirSync(outDir, { recursive: true });
const files = walk(source);
const manifest = {};
const missingCss = [];

for (const file of files) {
  const html = fs.readFileSync(file, 'utf8');
  const route = routeFromFile(file);
  let start = html.indexOf('<div data-elementor-type="wp-page"');
  let end = start >= 0 ? html.indexOf('</main>', start) : -1;
  if (start < 0 || end < 0) {
    start = html.indexOf('<main id="main"');
    const openEnd = html.indexOf('>', start);
    end = html.indexOf('</main>', openEnd);
    start = openEnd + 1;
  }
  if (start < 0 || end < 0) {
    console.log('skip', route);
    continue;
  }
  const chunk = clean(html.slice(start, end));
  const id = (chunk.match(/data-elementor-id="(\d+)"/) || [])[1] || '';
  const cssFile = id ? `post-${id}.css` : '';
  const hasCss = cssFile && fs.existsSync(path.join(cssDir, cssFile));
  if (cssFile && !hasCss) missingCss.push(`${route} ${cssFile}`);
  const relFile = route === '/' ? 'index.html' : `${route.slice(1)}.html`;
  const dest = path.join(outDir, relFile);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, chunk);
  manifest[route] = { id, css: hasCss ? cssFile : '', file: `/${relFile.replace(/\\/g, '/')}` };
}

const home = fs.readFileSync(path.join(source, 'index.html'), 'utf8');
const headerStart = home.indexOf('<div data-elementor-type="wp-post" data-elementor-id="9798"');
const headerEnd = home.indexOf('</header>', headerStart);
const footerStart = home.indexOf('<div data-elementor-type="wp-post" data-elementor-id="9887"');
const footerEnd = home.indexOf('</footer>', footerStart);
const customStart = home.indexOf('<style id="wp-custom-css">');
const customEnd = home.indexOf('</style>', customStart);
const customCss = customStart >= 0 ? home.slice(customStart + '<style id="wp-custom-css">'.length, customEnd) : '';

fs.writeFileSync(path.join(outDir, 'shell.json'), JSON.stringify({
  header: clean(home.slice(headerStart, headerEnd)),
  footer: clean(home.slice(footerStart, footerEnd)),
}));
fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2));
fs.writeFileSync(path.join(root, 'src', 'styles', 'wp-custom.css'), customCss.trim());

const core = [
  'frontend.min.css',
  'frontend.css',
  'elementor-frontend.min.css',
  'header-footer-elementor.css',
  'widget-heading.min.css',
  'widget-image.min.css',
  'widget-icon-list.min.css',
  'widget-image-gallery.min.css',
  'widget-divider.min.css',
  'widget-video.min.css',
  'widget-text-editor.min.css',
  'widget-social-icons.min.css',
  'smartslider.min.css',
  'swiper.min.css',
  'e-swiper.min.css',
  'elementor-icons.min.css',
  'post-176.css',
  'post-9798.css',
  'post-9887.css',
];
const posts = fs.readdirSync(cssDir).filter((name) => /^post-\d+\.css$/.test(name) && !core.includes(name));
const imports = [...core, ...posts].map((name) => `import '../../akits_scraped_resources/stylesheets/${name}';`).join('\n');
fs.writeFileSync(path.join(root, 'src', 'styles', 'scraped.js'), `${imports}\nimport './wp-custom.css';\nimport './original-fixes.css';\n`);

console.log('pages', Object.keys(manifest).length);
console.log('missing css', missingCss.length);
if (missingCss.length) console.log(missingCss.join('\n'));
