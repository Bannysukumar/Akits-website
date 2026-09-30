import { Link } from 'react-router-dom';
import { useState } from 'react';
import { siteInfo } from '../../utils/helpers';
import AnnouncementTicker from './AnnouncementTicker';
import Navbar from './Navbar';
import './Header.css';

function tickerItems() {
  const phones = (siteInfo.contact?.phones || [])
    .map((phone) => phone.replace('+91', '').trim())
    .join(', ');
  return [
    `Contact To Principal: ${phones}`,
    ...(siteInfo.announcement_ticker || []),
    'Application are invited for the post of Asst. Professors, Associate Professors, Professors in the department of CIVIL,EEE,MECH,ECE,CSE,AI&ML.CSE(DS) & MINING ENGINEERING, M.TECH(EPS),M.TECH(T.E),MBA, PHYSICS, CHEMISTRY, MATHS & ENGLISH.',
  ];
}

export default function Header() {
  const [logoOk, setLogoOk] = useState(true);

  return (
    <header className="header">
      <a className="skip-link" href="#main">Skip to content</a>
      <Link to="/" className="banner-link" aria-label={siteInfo.full_name}>
        {logoOk ? (
          <img
            className="banner-logo"
            src={siteInfo.logo}
            alt={siteInfo.full_name}
            onError={() => setLogoOk(false)}
          />
        ) : (
          <div className="banner-fallback">{siteInfo.full_name}</div>
        )}
      </Link>
      <Navbar />
      <div className="ticker-bar">
        <AnnouncementTicker items={tickerItems()} />
      </div>
    </header>
  );
}
