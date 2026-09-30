import fs from 'fs';

const dir = 'akits_scraped_resources/stylesheets';
const file = 'src/styles/scraped.js';
let source = fs.readFileSync(file, 'utf8');
const posts = fs.readdirSync(dir).filter((name) => /^post-\d+\.css$/.test(name));
const missing = posts.filter((name) => !source.includes(name));
if (!missing.length) {
  console.log('added 0');
  process.exit(0);
}
const lines = missing.map((name) => `import '../../akits_scraped_resources/stylesheets/${name}';`).join('\n');
source = source.replace("import './wp-custom.css';", `${lines}\nimport './wp-custom.css';`);
fs.writeFileSync(file, source);
console.log('added', missing.length);
console.log(missing.join('\n'));
