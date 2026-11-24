import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';
import type { ImageMetadata } from 'astro';

export interface Place { name: string; text: string; coords: [number, number] }
export interface Room {
  slug: string; name: string; area: number | null; beds: string | null;
  guests: number | null; price_from: number | null; text: string;
}
export interface Hotel {
  slug: string; site_url: string; noindex?: boolean; name: string; short_name: string; type: string;
  stars: number | null; city: string; city_prep: string; address: string;
  postal_code: string | null; region: string | null; coords: [number, number];
  rooms_total: number | null; price_from: number | null; currency: string;
  rating: { value: number; count: number; source: string; url: string | null } | null;
  contacts: { phone: string; phone_display: string; whatsapp: string | null; telegram: string | null; email: string | null };
  legal: { name: string; inn: string | null; ogrn: string | null };
  booking: { provider: 'bnovo' | 'link' | 'request'; url: string | null; lang?: string };
  analytics: { metrika_id: number | null };
  seo: { title: string; description: string };
  hero: { image: string; title: string; lead: string };
  highlights: { title: string; text: string }[];
  about: string;
  rooms: Room[];
  arrival: { steps: string[]; airport: { name: string; coords: [number, number] } | null; station: { name: string; coords: [number, number] } | null };
  taxi: { name: string; text: string; url: string }[];
  places: Place[];
  faq: { q: string; a: string }[];
}

const slug = process.env.HOTEL || 'prospekt';
const file = path.resolve(process.cwd(), 'hotels', `${slug}.yaml`);
export const hotel = yaml.load(fs.readFileSync(file, 'utf8')) as Hotel;

const all = import.meta.glob<{ default: ImageMetadata }>('/src/assets/hotels/**/*.{jpg,jpeg,png,webp}', { eager: true });
const base = `/src/assets/hotels/${hotel.slug}/`;
const byName = (a: string, b: string) => a.localeCompare(b, 'en', { numeric: true });

export function image(rel: string): ImageMetadata {
  const img = all[base + rel];
  if (!img) throw new Error(`Нет фото ${base + rel}`);
  return img.default;
}
export function images(dir: string): ImageMetadata[] {
  return Object.keys(all).filter((k) => k.startsWith(base + dir + '/')).sort(byName).map((k) => all[k].default);
}
export const roomImages = (r: Room) => images(`rooms/${r.slug}`);
export const hotelImages = () => images('hotel');

export function distanceKm([lat1, lon1]: [number, number], [lat2, lon2]: [number, number]) {
  const R = 6371, rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad, dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}
export const fmtKm = (km: number) => km < 1 ? `${Math.round(km * 10) * 100} м` : `${km.toFixed(1).replace('.', ',')} км`;
export const fmtPrice = (n: number) => n.toLocaleString('ru-RU').replace(/\u00a0|,/g, ' ') + ' ₽';
export const routeUrl = (to: [number, number], mode: 'auto' | 'pd' | 'mt' = 'pd', from?: [number, number]) =>
  `https://yandex.ru/maps/?rtext=${from ? from.join(',') : ''}~${to.join(',')}&rtt=${mode}`;
export const telUrl = () => `tel:${hotel.contacts.phone}`;
export const waUrl = (text?: string) => hotel.contacts.whatsapp
  ? `https://wa.me/${hotel.contacts.whatsapp}${text ? `?text=${encodeURIComponent(text)}` : ''}` : null;
export const bookingUrl = () => hotel.booking.url
  ? hotel.booking.url + (hotel.booking.lang ? `?lang=${hotel.booking.lang}` : '') : '/kontakty/#zayavka';
export const roomsWord = (n: number) => {
  const m10 = n % 10, m100 = n % 100;
  return m10 === 1 && m100 !== 11 ? 'номер' : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? 'номера' : 'номеров';
};
