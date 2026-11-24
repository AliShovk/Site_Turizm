import type { APIRoute } from 'astro';
import { hotel } from '../lib/hotel';
export const GET: APIRoute = ({ site }) =>
  new Response(hotel.noindex
    ? 'User-agent: *\nDisallow: /\n'
    : `User-agent: *\nAllow: /\n\nSitemap: ${new URL('sitemap-index.xml', site).href}\n`);
