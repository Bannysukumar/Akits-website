import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { FaBars, FaChevronDown, FaChevronRight, FaSearch, FaTimes } from 'react-icons/fa';
import { navigation, searchPages, toRoute } from '../../utils/helpers';
import './Navbar.css';

function branchActive(item, pathname) {
  const route = toRoute(item.path);
  if (route && route === pathname) return true;
  return item.children?.some((child) => branchActive(child, pathname)) || false;
}

function DesktopItem({ item, pathname }) {
  const route = toRoute(item.path);
  const hasChildren = item.children?.length > 0;
  const active = branchActive(item, pathname);

  return (
    <li className={`nav-item${active ? ' is-active' : ''}`}>
      {route ? (
        <NavLink to={route} end={route === '/'}>
          {item.label}
          {hasChildren && <FaChevronDown size={10} />}
        </NavLink>
      ) : (
        <button type="button" className="nav-trigger">
          {item.label}
          {hasChildren && <FaChevronDown size={10} />}
        </button>
      )}
      {hasChildren && (
        <div className="dropdown">
          {item.children.map((child) => (
            <DropdownEntry key={child.label} item={child} />
          ))}
        </div>
      )}
    </li>
  );
}

function DropdownEntry({ item }) {
  const route = toRoute(item.path);
  const hasChildren = item.children?.length > 0;

  return (
    <div className="dropdown-entry">
      {route ? (
        <NavLink to={route}>
          {item.label}
          {hasChildren && <FaChevronRight size={10} />}
        </NavLink>
      ) : (
        <button type="button" className="sub-trigger">
          {item.label}
          {hasChildren && <FaChevronRight size={10} />}
        </button>
      )}
      {hasChildren && (
        <div className="flyout">
          {item.children.map((child) => {
            const childRoute = toRoute(child.path);
            if (!childRoute) return <span key={child.label}>{child.label}</span>;
            return (
              <NavLink key={child.label} to={childRoute}>
                {child.label}
              </NavLink>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MobileItems({ items, depth = 0 }) {
  const [open, setOpen] = useState('');

  return (
    <ul className={depth ? 'nested' : 'mobile-list'}>
      {items.map((item) => {
        const route = toRoute(item.path);
        const hasChildren = item.children?.length > 0;
        const isOpen = open === item.label;
        return (
          <li key={`${item.label}-${depth}`}>
            <div className="mobile-row">
              {route ? (
                <Link to={route}>{item.label}</Link>
              ) : (
                <button type="button" className="grow" onClick={() => setOpen(isOpen ? '' : item.label)}>
                  {item.label}
                </button>
              )}
              {hasChildren && (
                <button
                  type="button"
                  className="chev"
                  aria-label={`Expand ${item.label}`}
                  onClick={() => setOpen(isOpen ? '' : item.label)}
                >
                  <FaChevronDown size={12} style={{ transform: isOpen ? 'rotate(180deg)' : undefined }} />
                </button>
              )}
            </div>
            {hasChildren && isOpen && <MobileItems items={item.children} depth={depth + 1} />}
          </li>
        );
      })}
    </ul>
  );
}

export default function Navbar() {
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const results = searchPages(query);

  useEffect(() => {
    setMobileOpen(false);
    setSearchOpen(false);
    setQuery('');
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  return (
    <nav className="navbar" aria-label="Primary">
      <div className="navbar-inner">
        <button
          type="button"
          className="menu-toggle"
          aria-label="Open menu"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(true)}
        >
          <FaBars />
        </button>
        <ul className="desktop-nav">
          {navigation.map((item) => (
            <DesktopItem key={item.label} item={item} pathname={pathname} />
          ))}
        </ul>
        <form className="nav-search" onSubmit={(event) => event.preventDefault()}>
          <input
            value={query}
            placeholder="Search here..."
            aria-label="Search here..."
            onChange={(event) => {
              setQuery(event.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
          />
          <button type="submit" aria-label="Search">
            <FaSearch />
          </button>
          {searchOpen && query.trim().length >= 2 && (
            <div className="search-panel">
              {results.length === 0 && <p className="search-empty">No matching pages.</p>}
              <ul>
                {results.map((item) => (
                  <li key={item.route}>
                    <Link to={item.route}>
                      {item.title || item.label}
                      <small>{item.route}</small>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </form>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="drawer-backdrop"
              onClick={() => setMobileOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.aside
              className="mobile-drawer"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.28 }}
            >
              <div className="drawer-head">
                <strong>Menu</strong>
                <button type="button" aria-label="Close menu" onClick={() => setMobileOpen(false)}>
                  <FaTimes />
                </button>
              </div>
              <MobileItems items={navigation} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </nav>
  );
}
