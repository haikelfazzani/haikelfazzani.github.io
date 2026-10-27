import { writeFile } from 'node:fs/promises';

// The haikelfazzani.github.io user site publishes at the domain root.
// Preserve Astro's root-relative links and serve underscore-prefixed assets.
await writeFile('dist/.nojekyll', '');
console.log('Prepared dist for https://haikelfazzani.github.io/');
