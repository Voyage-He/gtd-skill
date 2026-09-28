'use strict';

const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const manifest = fs.readFileSync(path.join(root, 'plugin.yaml'), 'utf8');
const version = manifest.match(/^version:\s*"([^"]+)"\s*$/m)?.[1];
if (version !== pkg.version) throw new Error('npm and Hermes plugin versions must match');
for (const file of [...pkg.files, 'README.md', 'LICENSE']) {
  if (!fs.statSync(path.join(root, file)).isFile()) throw new Error(`Missing release file: ${file}`);
}
console.log(`Validated ${pkg.name}@${pkg.version}`);
