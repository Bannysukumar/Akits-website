import { FaFacebookF, FaInstagram, FaTwitter, FaYoutube } from 'react-icons/fa';
import { footerInfo, siteInfo } from '../../utils/helpers';
import './Footer.css';

const ICONS = {
  facebook: FaFacebookF,
  twitter: FaTwitter,
  youtube: FaYoutube,
  instagram: FaInstagram,
};

export default function Footer() {
  const heading = footerInfo.footer_text?.[0] || 'Affiliations & Recognitions';
  const social = Object.entries(siteInfo.social_links || {});

  return (
    <footer className="footer">
      <div className="affiliations">
        <div className="container">
          <h2>{heading}</h2>
          <div className="logo-row">
            {(siteInfo.affiliation_logos || []).map((src) => (
              <img key={src} src={src} alt="" />
            ))}
          </div>
        </div>
      </div>
      <div className="footer-bottom">
        <p>{siteInfo.copyright}</p>
        <div className="visitor">
          <span>Visitors</span>
          <strong>1,84,256</strong>
        </div>
        <div className="footer-social">
          {social.map(([platform, url]) => {
            const Icon = ICONS[platform] || FaFacebookF;
            return (
              <a key={platform} href={url} target="_blank" rel="noreferrer" aria-label={platform}>
                <Icon />
              </a>
            );
          })}
        </div>
      </div>
    </footer>
  );
}
