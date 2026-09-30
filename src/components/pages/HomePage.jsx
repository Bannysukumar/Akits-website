import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FaFacebookF, FaInstagram, FaTwitter, FaYoutube } from 'react-icons/fa';
import HeroSlider from '../common/HeroSlider';
import {
  decodeHtml,
  getPage,
  heroSlides,
  matchDocument,
  matchInternalRoute,
  siteInfo,
} from '../../utils/helpers';

const SOCIAL = {
  facebook: FaFacebookF,
  twitter: FaTwitter,
  youtube: FaYoutube,
  instagram: FaInstagram,
};

function sectionTitle(page, pattern) {
  const heading = page?.headings?.find((item) => pattern.test(item.text || ''));
  return heading ? decodeHtml(heading.text) : '';
}

function NewsLabel({ text }) {
  const decoded = decodeHtml(text);
  const isNew = /^new\b/i.test(decoded);
  const label = isNew ? decoded.replace(/^new\s*/i, '') : decoded;
  return (
    <span>
      {isNew && <em className="new-badge">NEW</em>}
      {label}
    </span>
  );
}

export default function HomePage() {
  const page = getPage('/');
  const slides = heroSlides(page, 16).filter((slide) => /\.(jpe?g|webp)(\?|$)/i.test(slide.src));
  const news = page?.lists?.[0]?.items || [];
  const quick = page?.lists?.[1]?.items || [];
  const newsLoop = news.length ? [...news, ...news] : [];
  const partners = siteInfo.knowledge_partners || [];
  const social = Object.entries(siteInfo.social_links || {});
  const documents = page?.documents || [];

  useEffect(() => {
    document.title = page?.title ? `${page.title} | ${siteInfo.site_name}` : siteInfo.full_name;
    const meta = document.querySelector('meta[name="description"]');
    if (meta && (page?.meta_description || siteInfo.meta?.description)) {
      meta.content = page?.meta_description || siteInfo.meta.description;
    }
  }, [page]);

  return (
    <div className="home">
      <div className="home-split">
        <HeroSlider slides={slides.length ? slides : heroSlides(page, 8)} />
        <aside className="home-side">
          <h2 className="gold-title">{sectionTitle(page, /latest news/i)}</h2>
          <div className="side-box news-clip">
            <div className="news-track">
              {newsLoop.map((item, index) => {
                const doc = matchDocument(item, documents);
                const route = matchInternalRoute(item);
                const body = <NewsLabel text={item} />;
                if (doc) {
                  return (
                    <a className="news-item" key={`${item}-${index}`} href={doc.url} target="_blank" rel="noreferrer">
                      {body}
                    </a>
                  );
                }
                if (route) {
                  return (
                    <Link className="news-item" key={`${item}-${index}`} to={route}>
                      {body}
                    </Link>
                  );
                }
                return <div className="news-item" key={`${item}-${index}`}>{body}</div>;
              })}
            </div>
          </div>

          <h2 className="gold-title">{sectionTitle(page, /quick links/i)}</h2>
          <div className="side-box">
            <ul className="quick-links">
              {quick.map((item) => {
                const doc = matchDocument(item, documents);
                const route = matchInternalRoute(item);
                const label = <><span className="ql-dot" /><span>{decodeHtml(item)}</span></>;
                if (doc) {
                  return (
                    <li key={item}>
                      <a className="quick-link" href={doc.url} target="_blank" rel="noreferrer">{label}</a>
                    </li>
                  );
                }
                if (route) {
                  return (
                    <li key={item}>
                      <Link className="quick-link" to={route}>{label}</Link>
                    </li>
                  );
                }
                return (
                  <li key={item}>
                    <div className="quick-link">{label}</div>
                  </li>
                );
              })}
            </ul>
          </div>
        </aside>
      </div>

      <section className="partner-block">
        <h2>{sectionTitle(page, /knowledge partners/i)}</h2>
        <div className="partner-row">
          {partners.map((partner, index) => (
            <h3 key={partner}>{index + 1}. {partner}</h3>
          ))}
        </div>
      </section>

      <section className="follow">
        <h3>{sectionTitle(page, /follow us/i)}</h3>
        <div className="social-row">
          {social.map(([platform, url]) => {
            const Icon = SOCIAL[platform] || FaFacebookF;
            return (
              <a key={platform} className={platform} href={url} target="_blank" rel="noreferrer" aria-label={platform}>
                <Icon />
              </a>
            );
          })}
        </div>
      </section>
    </div>
  );
}
