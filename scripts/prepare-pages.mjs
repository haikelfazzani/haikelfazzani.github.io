import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

// Prepare Astro's static output for this repository's GitHub Pages project URL.
const base = '/haikelfazzani';
const prefix = value => value.startsWith(`${base}/`) || value === base ? value : `${base}${value}`;
async function prepare(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) await prepare(path);
    else if (/\.(html|css)$/.test(entry.name)) {
      let content = await readFile(path, 'utf8');
      if (entry.name.endsWith('.html')) {
        content = content.replace(/\b(href|src|action)=(['"])(\/(?!\/)[^'"\s]*)\2/g,
          (_, attribute, quote, url) => `${attribute}=${quote}${prefix(url)}${quote}`);
      }
      content = content.replace(/url\((['"]?)(\/(?!\/)[^)'"\s]*)\1\)/g,
        (_, quote, url) => `url(${quote}${prefix(url)}${quote})`);
      await writeFile(path, content);
    }
  }
}
await prepare('dist');
await writeFile('dist/.nojekyll', '');
console.log(`Prepared dist for https://haikelfazzani.github.io${base}/`);
