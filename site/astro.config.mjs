import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import fs from 'node:fs';
import yaml from 'js-yaml';

const hotel = yaml.load(fs.readFileSync(`./hotels/${process.env.HOTEL || 'prospekt'}.yaml`, 'utf8'));

export default defineConfig({
  site: hotel.site_url,
  trailingSlash: 'always',
  integrations: [sitemap()],
  build: { inlineStylesheets: 'always' },
  image: { responsiveStyles: false },
});
