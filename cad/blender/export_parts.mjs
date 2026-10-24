// Export the reference parts from the Push Assist Onshape doc as STL (mm) for the Blender concept.
// Usage: node cad/blender/export_parts.mjs
// The STL endpoint answers with a redirect, and fetch drops auth headers when following it,
// so each hop is signed here by hand.
import { createHmac, randomBytes } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { credentials } from '../../../onshape-slopify/src/env.mjs';

function signed(url) {
  const { accessKey, secretKey } = credentials();
  const u = new URL(url);
  const date = new Date().toUTCString();
  const nonce = randomBytes(24).toString('hex').slice(0, 25);
  const toSign = `GET\n${nonce}\n${date}\napplication/json\n${u.pathname}\n${u.search.slice(1)}\n`.toLowerCase();
  const sig = createHmac('sha256', secretKey).update(toSign, 'utf8').digest('base64');
  return { Date: date, 'On-Nonce': nonce, 'Content-Type': 'application/json',
    Accept: 'application/vnd.onshape.v1+octet-stream', Authorization: `On ${accessKey}:HmacSHA256:${sig}` };
}

async function getFollowing(url) {
  for (let hop = 0; hop < 5; hop++) {
    const res = await fetch(url, { headers: signed(url), redirect: 'manual' });
    if (res.status >= 300 && res.status < 400) { url = new URL(res.headers.get('location'), url).href; continue; }
    if (!res.ok) throw new Error(`${res.status} on ${url}: ${(await res.text()).slice(0, 200)}`);
    return res.text();
  }
  throw new Error('too many redirects');
}

const DID = '132253c3fd9fd0858faa53fc';
const WID = 'bd9088c1173709e073d7242a';
const PARTS = {
  load_cell: '334917d38807f4c558855ea1',
  hx711: 'a2a052558e83984aac002832',
  esp32_p4: '67e84d7a91b946d660d6ada3',
  rj45_coupler: '9b46e8d6355ab215f3954062',
  mtb_grip: 'b8c2f858f9fdfd96012a3b90',
};

const out = join(dirname(fileURLToPath(import.meta.url)), 'parts');
for (const [name, eid] of Object.entries(PARTS)) {
  const q = new URLSearchParams({ mode: 'text', units: 'millimeter', grouping: 'true', angleTolerance: '0.05', chordTolerance: '0.02' });
  const stl = await getFollowing(`https://cad.onshape.com/api/v10/partstudios/d/${DID}/w/${WID}/e/${eid}/stl?${q}`);
  if (typeof stl !== 'string' || !stl.startsWith('solid')) throw new Error(`${name}: not an STL`);
  writeFileSync(join(out, `${name}.stl`), stl);
  console.log(name, (stl.match(/facet normal/g) || []).length, 'facets');
}
