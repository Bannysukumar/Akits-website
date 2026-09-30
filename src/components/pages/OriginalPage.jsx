import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Spinner from '../common/Spinner';
import ContactPage from './ContactPage';
import DynamicPage from './DynamicPage';
import { getPage, normalizePath, siteInfo } from '../../utils/helpers';

function showSlide(slider, index) {
  const slides = [...slider.querySelectorAll('.n2-ss-slide')];
  const backgrounds = [...slider.querySelectorAll('.n2-ss-slide-background')];
  if (!slides.length) return;
  const next = ((index % slides.length) + slides.length) % slides.length;
  slider.dataset.index = String(next);
  slider.classList.add('n2-ss-loaded');
  slides.forEach((slide, item) => slide.classList.toggle('akits-on', item === next));
  backgrounds.forEach((background, item) => background.classList.toggle('akits-on', item === next));
}

export default function OriginalPage() {
  const { pathname } = useLocation();
  const path = normalizePath(pathname);
  const [html, setHtml] = useState('');
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancel = false;
    setStatus('loading');
    setHtml('');
    const file = path === '/' ? '/original/index.html' : `/original${path}.html`;
    fetch(file)
      .then((response) => {
        if (!response.ok) throw new Error('missing');
        return response.text();
      })
      .then((text) => {
        if (cancel) return;
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
    document.title = !name || path === '/'
      ? siteInfo.full_name || 'AKITS'
      : /AKITS/i.test(name) ? name : `${name} | AKITS`;
    const description = page?.meta_description;
    if (description) {
      let meta = document.querySelector('meta[name="description"]');
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('name', 'description');
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', description);
    }
    document.querySelectorAll('.n2-ss-slider').forEach((slider) => showSlide(slider, 0));
    const timer = setInterval(() => {
      document.querySelectorAll('.n2-ss-slider').forEach((slider) => {
        showSlide(slider, Number(slider.dataset.index || 0) + 1);
      });
    }, 5000);
    const onArrow = (event) => {
      const { slider, direction } = event.detail || {};
      if (!slider) return;
      showSlide(slider, Number(slider.dataset.index || 0) + direction);
    };
    window.addEventListener('akits-slide', onArrow);
    return () => {
      clearInterval(timer);
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
