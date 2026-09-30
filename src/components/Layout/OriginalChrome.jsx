import { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { searchPages } from '../../utils/helpers';
import ScrollToTop from '../common/ScrollToTop';

export default function OriginalChrome() {
  const [shell, setShell] = useState(null);
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    fetch('/original/shell.json')
      .then((response) => response.json())
      .then(setShell)
      .catch(() => setShell({ header: '', footer: '' }));
  }, []);

  useEffect(() => {
    const root = document.querySelector('.akits-original');
    if (!root) return;
    root.querySelectorAll('.current-menu-item, .current_page_item').forEach((item) => {
      item.classList.remove('current-menu-item', 'current_page_item');
    });
    root.querySelectorAll('a.hfe-menu-item, a.hfe-sub-menu-item').forEach((link) => {
      if (link.getAttribute('href') === pathname) {
        link.parentElement?.classList.add('current-menu-item');
      }
    });
  }, [pathname, shell]);

  const onClick = (event) => {
    const toggle = event.target.closest('.hfe-nav-menu__toggle');
    if (toggle) {
      event.preventDefault();
      toggle.classList.toggle('hfe-active-menu');
      return;
    }

    const arrow = event.target.closest('.nextend-arrow-previous, .nextend-arrow-next');
    if (arrow) {
      event.preventDefault();
      const slider = arrow.closest('.n2-ss-slider');
      if (slider) window.dispatchEvent(new CustomEvent('akits-slide', {
        detail: { slider, direction: arrow.classList.contains('nextend-arrow-next') ? 1 : -1 },
      }));
      return;
    }

    const link = event.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    if (!href.startsWith('/') || href.startsWith('//')) return;
    event.preventDefault();
    navigate(href);
  };

  const onSubmit = (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    event.preventDefault();
    if (form.classList.contains('wpcf7-form') || form.querySelector('.wpcf7-form-control')) {
      const note = document.createElement('p');
      note.className = 'akits-thanks';
      note.textContent = 'Thank you. Your message has been received.';
      form.replaceWith(note);
      return;
    }
    const input = form.querySelector('input[type="search"], input[name="s"], input');
    const query = input?.value?.trim();
    if (!query) return;
    const hit = searchPages(query)[0];
    if (hit?.route) navigate(hit.route);
  };

  if (!shell) return null;

  return (
    <div className="akits-original elementor-kit-176" onClick={onClick} onSubmit={onSubmit}>
      <ScrollToTop />
      <header id="masthead" dangerouslySetInnerHTML={{ __html: shell.header }} />
      <main id="main" className="site-main">
        <Outlet />
      </main>
      <footer id="colophon" dangerouslySetInnerHTML={{ __html: shell.footer }} />
    </div>
  );
}
