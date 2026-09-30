import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Spinner from '../common/Spinner';
import ContactPage from './ContactPage';
import DynamicPage from './DynamicPage';
import { getPage, normalizePath, siteInfo } from '../../utils/helpers';

const SITE = 'https://akits-ac-in.vercel.app';

function setMeta(selector, attributes, content) {
  if (!content) return;
  let tag = document.head.querySelector(selector);
  if (!tag) {
    tag = document.createElement('meta');
    Object.entries(attributes).forEach(([key, value]) => tag.setAttribute(key, value));
    document.head.appendChild(tag);
  }
  tag.setAttribute('content', content);
}

const pageCache = new Map();

function sliderParts(slider) {
  const slides = [...slider.querySelectorAll('.n2-ss-slider-4 > .n2-ss-slide')];
  const backgrounds = [...slider.querySelectorAll('.n2-ss-slide-backgrounds > .n2-ss-slide-background')];
  return { slides, backgrounds };
}

function showSlide(slider, index) {
  const { slides, backgrounds } = sliderParts(slider);
  const count = Math.max(slides.length, backgrounds.length);
  if (!count) return;
  const next = ((index % count) + count) % count;
  if (slider.dataset.index === String(next) && slider.classList.contains('n2-ss-loaded')) return;
  slider.dataset.index = String(next);
  slider.classList.add('n2-ss-loaded');
  slides.forEach((slide, item) => slide.classList.toggle('akits-on', item === next));
  backgrounds.forEach((background, item) => {
    const active = item === next;
    background.classList.toggle('akits-on', active);
    const image = background.querySelector('img');
    if (!image) return;
    const src = image.getAttribute('src');
    if (src && !image.dataset.held) image.dataset.held = src;
    if (!active) return;
    image.dataset.shown = '1';
    if (!src && image.dataset.held) image.src = image.dataset.held;
    image.loading = 'eager';
  });
  backgrounds.forEach((background) => {
    if (background.classList.contains('akits-on')) return;
    const image = background.querySelector('img');
    if (image && !image.dataset.shown) image.removeAttribute('src');
  });
}

export default function OriginalPage() {
  const { pathname } = useLocation();
  const path = normalizePath(pathname);
  const [html, setHtml] = useState('');
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    const cached = pageCache.get(path);
    if (cached) {
      setHtml(cached);
      setStatus('ready');
      return undefined;
    }
    let cancel = false;
    setStatus('loading');
    const file = path === '/' ? '/original/index.html' : `/original${path}.html`;
    fetch(file)
      .then((response) => {
        if (!response.ok) throw new Error('missing');
        return response.text();
      })
      .then((text) => {
        if (cancel) return;
        pageCache.set(path, text);
        setHtml(text);
        setStatus('ready');
      })
      .catch(() => {
        if (!cancel) setStatus('missing');
      });
    return () => {
      cancel = true;
    };
  }, [path]);

  useEffect(() => {
    if (status !== 'ready') return undefined;
    const page = getPage(path);
    const heading = document.querySelector('.akits-original main h1, .akits-original main h2, .akits-original main h3');
    const name = page?.title || heading?.textContent?.trim();
    const title = !name || path === '/'
      ? siteInfo.full_name || 'AKITS'
      : /AKITS/i.test(name) ? name : `${name} | AKITS`;
    document.title = title;
    const url = path === '/' ? `${SITE}/` : `${SITE}${path}`;
    const canonical = document.querySelector('link[rel="canonical"]');
    if (canonical) canonical.setAttribute('href', url);
    const description = page?.meta_description
      || 'Abdul Kalam Institute of Technological Sciences (AKITS), an autonomous engineering college in Kothagudem, Telangana.';
    setMeta('meta[name="description"]', { name: 'description' }, description);
    setMeta('meta[property="og:title"]', { property: 'og:title' }, title);
    setMeta('meta[property="og:description"]', { property: 'og:description' }, description);
    setMeta('meta[property="og:url"]', { property: 'og:url' }, url);
    document.querySelectorAll('video').forEach((video) => {
      video.preload = 'none';
      video.removeAttribute('autoplay');
    });
    document.querySelectorAll('.n2-ss-slider').forEach((slider) => showSlide(slider, 0));
    const onArrow = (event) => {
      const { slider, direction } = event.detail || {};
      if (!slider) return;
      showSlide(slider, Number(slider.dataset.index || 0) + direction);
    };
    window.addEventListener('akits-slide', onArrow);
    return () => {
      window.removeEventListener('akits-slide', onArrow);
    };
  }, [status, html, path]);

  if (status === 'loading') return <Spinner />;
  if (status === 'missing') {
    if (path === '/contact-us') return <ContactPage />;
    return <DynamicPage />;
  }
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
