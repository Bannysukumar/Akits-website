import { NavLink } from 'react-router-dom';

export default function Sidebar({ title = 'Quick Links', links = [] }) {
  if (!links.length) return null;
  return (
    <aside className="sidebar">
      <h2>{title}</h2>
      <ul>
        {links.map((link) => (
          <li key={link.route}>
            <NavLink to={link.route}>{link.label}</NavLink>
          </li>
        ))}
      </ul>
    </aside>
  );
}
