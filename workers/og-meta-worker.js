/**
 * Cloudflare Worker: SSR Meta Tags for Deep Links
 *
 * Intercepts social crawler requests to missingparkhistory.org/?id=X&park=CODE
 * and injects entry-specific Open Graph / Twitter Card meta tags so that
 * shared links show the correct park name, description, and image.
 *
 * SETUP:
 * 1. Create a Cloudflare account and add missingparkhistory.org
 * 2. In Workers & Pages → Create Worker → paste this script
 * 3. Add a Route: missingparkhistory.org/* → this worker
 * 4. Upload parkData.json to a KV namespace called PARK_DATA,
 *    or fetch it at runtime (see PARK_DATA_URL below).
 *
 * The worker only modifies responses for social bot user agents.
 * Normal visitors get the original page untouched.
 */

const PARK_DATA_URL = 'https://missingparkhistory.org/data/parkData.json';
const SITE_URL = 'https://missingparkhistory.org';
const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;

// Social crawler user agent patterns
const BOT_PATTERNS = [
  'facebookexternalhit',
  'Facebot',
  'Twitterbot',
  'LinkedInBot',
  'Slackbot',
  'WhatsApp',
  'Discordbot',
  'TelegramBot',
  'Applebot',
  'Pinterest',
  'Embedly',
  'Quora Link Preview',
  'Showyoubot',
  'vkShare',
  'redditbot',
];

// Parks with dedicated pages and OG images
const PARKS_WITH_PAGES = {
  "EVER": "everglades-np", "CARI": "cane-river-creole-nhp",
  "SEMO": "selma-to-montgomery-nht", "MACA": "mammoth-cave-np",
  "CAHA": "cape-hatteras-ns", "CHOH": "cando-canal-nhp",
  "ANTI": "antietam-nb", "NATR": "natchez-trace-parkway",
  "CHPI": "charles-pinckney-nhs", "FOSU": "fort-sumter-and-fort-moultrie-nhp",
  "FRRI": "fire-island-ns", "LOWE": "lower-delaware-wsr",
  "INDE": "independence-nhp", "NAMA": "national-mall",
  "BLRI": "blue-ridge-parkway", "CUGA": "cumberland-gap-nhp",
  "YOSE": "yosemite-np", "FORA": "fort-raleigh-nhs",
  "STRI": "stones-river-nb", "ANDE": "andersonville-nhs"
};

function isSocialBot(userAgent) {
  if (!userAgent) return false;
  const ua = userAgent.toLowerCase();
  return BOT_PATTERNS.some(pattern => ua.includes(pattern.toLowerCase()));
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function stripHtml(str) {
  return str.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').trim();
}

async function fetchParkData() {
  // Try KV first (faster), fall back to fetch
  // If using KV: const data = await PARK_DATA.get('all', { type: 'json' });
  const resp = await fetch(PARK_DATA_URL);
  if (!resp.ok) return null;
  return resp.json();
}

function buildMetaHtml(entry, entryId) {
  const parkName = escapeHtml(entry.park || 'Unknown Park');
  const state = escapeHtml(entry.state || '');
  const code = entry.code || '';
  const status = (entry.status || '').replace(/&mdash;/g, '—');

  // Build description from narrative
  let desc = '';
  if (entry.narrative) {
    desc = stripHtml(entry.narrative);
    if (desc.length > 200) desc = desc.substring(0, 197) + '...';
  } else {
    desc = `Entry #${entryId} at ${parkName} — flagged or removed under Secretary's Order 3431.`;
  }
  desc = escapeHtml(desc);

  const title = escapeHtml(`${parkName} — Missing Park History`);
  const url = `${SITE_URL}/?id=${entryId}&park=${code}`;

  // Use park-specific OG image if available, otherwise default
  const slug = PARKS_WITH_PAGES[code];
  const ogImage = slug
    ? `${SITE_URL}/og-parks/${slug}.png`
    : DEFAULT_OG_IMAGE;

  return `
    <title>${title}</title>
    <meta name="description" content="${desc}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="${url}">
    <meta property="og:title" content="${title}">
    <meta property="og:description" content="${desc}">
    <meta property="og:image" content="${ogImage}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Missing Park History">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="${title}">
    <meta name="twitter:description" content="${desc}">
    <meta name="twitter:image" content="${ogImage}">
  `;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const userAgent = request.headers.get('User-Agent') || '';

    // Only intercept bot requests to the homepage with deep link params
    if (!isSocialBot(userAgent)) {
      return fetch(request);
    }

    const entryId = url.searchParams.get('id');
    const parkCode = url.searchParams.get('park');

    // No deep link params — let the normal page serve
    if (!entryId && !parkCode) {
      return fetch(request);
    }

    try {
      const parkData = await fetchParkData();
      if (!parkData) return fetch(request);

      let entry = null;

      // Look up by entry ID first
      if (entryId && parkData[entryId]) {
        entry = parkData[entryId];
      }
      // Fall back to first entry for this park code
      else if (parkCode) {
        for (const [id, e] of Object.entries(parkData)) {
          if (e.code === parkCode) {
            entry = e;
            break;
          }
        }
      }

      if (!entry) return fetch(request);

      // Fetch the original page
      const originalResponse = await fetch(request);
      const html = await originalResponse.text();

      // Build replacement meta tags
      const metaHtml = buildMetaHtml(entry, entryId || '');

      // Replace the <head> section's meta tags
      const modifiedHtml = html
        .replace(/<title>[^<]*<\/title>/, '') // Remove original title
        .replace(/<!-- Core SEO -->[\s\S]*?<!-- Open Graph -->/, `<!-- Core SEO (SSR) -->\n${metaHtml}\n<!-- Open Graph -->`)
        .replace(/<meta property="og:[^>]*>/g, '') // Remove original OG tags
        .replace(/<meta name="twitter:[^>]*>/g, ''); // Remove original Twitter tags

      return new Response(modifiedHtml, {
        headers: {
          ...Object.fromEntries(originalResponse.headers),
          'Content-Type': 'text/html;charset=UTF-8',
        },
      });

    } catch (err) {
      // On any error, serve the original page
      return fetch(request);
    }
  },
};
