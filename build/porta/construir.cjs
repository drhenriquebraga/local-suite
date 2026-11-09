const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const esbuild = require('esbuild');

const AQUI = __dirname;
const SAIDA = path.join(AQUI, '..', '..', 'app', 'porta', 'porta.js');

function sha256(arquivo) {
  return crypto.createHash('sha256').update(fs.readFileSync(arquivo)).digest('hex');
}

async function construir() {
  await esbuild.build({
    entryPoints: [path.join(AQUI, 'app.mjs')],
    outfile: SAIDA,
    bundle: true,
    format: 'iife',
    target: ['chrome110', 'edge110'],
    minify: true,
    legalComments: 'none',
    charset: 'utf8'
  });
  const carimbo = {
    'app.mjs': sha256(path.join(AQUI, 'app.mjs')),
    'beam-renderer.mjs': sha256(path.join(AQUI, 'beam-renderer.mjs')),
    'package-lock.json': sha256(path.join(AQUI, 'package-lock.json')),
    'porta.js': sha256(SAIDA)
  };
  fs.writeFileSync(path.join(AQUI, 'carimbo.json'), JSON.stringify(carimbo, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({ porta: SAIDA, bytes: fs.statSync(SAIDA).size, carimbo }));
}

construir().catch(erro => { console.error(erro); process.exitCode = 1; });
