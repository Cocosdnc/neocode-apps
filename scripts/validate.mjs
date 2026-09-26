// Checks public/apps.json before it is published, so a typo never reaches the phones.
// Run: node scripts/validate.mjs
import { readFileSync, existsSync } from 'node:fs';

const BASE_URL = 'https://cocosdnc.github.io/neocode-apps/';
const errors = [];
let data;

try {
  data = JSON.parse(readFileSync('public/apps.json', 'utf8'));
} catch (e) {
  console.error(`apps.json n'est pas un JSON valide : ${e.message}`);
  process.exit(1);
}

if (data.schemaVersion !== 1) errors.push('schemaVersion doit valoir 1');
if (!Array.isArray(data.apps) || data.apps.length === 0) errors.push('"apps" doit être une liste non vide');

const isHttps = (s) => typeof s === 'string' && /^https:\/\/\S+$/.test(s);
const seen = new Set();

for (const [i, app] of (data.apps ?? []).entries()) {
  const at = `apps[${i}] (${app?.id ?? '?'})`;
  if (!/^[a-z0-9-]+$/.test(app.id ?? '')) errors.push(`${at}: id doit être en minuscules, chiffres et tirets`);
  if (seen.has(app.id)) errors.push(`${at}: id en double`);
  seen.add(app.id);
  if (!app.name) errors.push(`${at}: name manquant`);
  if (typeof app.active !== 'boolean') errors.push(`${at}: active doit être true ou false`);
  for (const field of ['tagline', 'description']) {
    if (!app[field]?.en) errors.push(`${at}: ${field}.en manquant (l'anglais sert de secours)`);
  }
  if (!isHttps(app.icon)) errors.push(`${at}: icon doit être une URL https`);
  else if (app.icon.startsWith(BASE_URL) && !existsSync(`public/${app.icon.slice(BASE_URL.length)}`)) {
    errors.push(`${at}: l'icône ${app.icon} n'existe pas dans public/`);
  }
  if (app.color && !/^#[0-9a-fA-F]{6}$/.test(app.color)) errors.push(`${at}: color doit être au format #RRGGBB`);
  if (!isHttps(app.website)) errors.push(`${at}: website doit être une URL https`);
  if (app.scheme && !/^[a-z][a-z0-9+.-]*:\/\/$/.test(app.scheme)) errors.push(`${at}: scheme doit ressembler à "monapp://"`);
  for (const os of ['android', 'ios']) {
    const url = app[os]?.storeUrl;
    if (url && !isHttps(url)) errors.push(`${at}: ${os}.storeUrl doit être vide ou une URL https`);
  }
}

if (errors.length) {
  console.error(`apps.json contient ${errors.length} erreur(s) :\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log(`apps.json OK (${data.apps.length} apps)`);
