import { useState } from 'react';
import { FaEnvelope, FaMapMarkerAlt, FaPhoneAlt } from 'react-icons/fa';
import PageShell from '../common/PageShell';
import Sidebar from '../common/Sidebar';
import { childLinks, navLinks, siteInfo } from '../../utils/helpers';

export default function ContactPage() {
  const fields = siteInfo.contact.contact_form?.fields || [];
  const required = new Set(siteInfo.contact.contact_form?.required_fields || []);
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});
  const [sent, setSent] = useState(false);

  const links = [
    ...navLinks.filter((link) => ['/about-us', '/rti', '/alumni'].includes(link.route)),
    ...childLinks('Admissions'),
    ...childLinks('Gallery'),
  ];

  const page = {
    route: '/contact-us',
    title: navLinks.find((link) => link.route === '/contact-us')?.label || 'Contact Us',
    meta_description: siteInfo.meta?.description || '',
    breadcrumbs: [
      { name: 'Home', url: 'https://akits.ac.in/' },
      { name: 'Contact Us', url: '' },
    ],
  };

  const onSubmit = (event) => {
    event.preventDefault();
    const next = {};
    fields.forEach((field) => {
      const value = values[field]?.trim() || '';
      if (required.has(field) && !value) next[field] = 'This field is required';
      if (/email/i.test(field) && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        next[field] = 'Enter a valid email address';
      }
    });
    setErrors(next);
    if (Object.keys(next).length === 0) setSent(true);
  };

  const mapQuery = encodeURIComponent(siteInfo.contact.google_maps_embed_query || siteInfo.full_name);

  return (
    <PageShell page={page}>
      <div className="contact-grid">
        <section className="card contact-card">
          <h2>{page.title}</h2>
          {sent ? (
            <p className="success-note">Thank you. Your message has been received.</p>
          ) : (
            <form className="form-grid" onSubmit={onSubmit} noValidate>
              <div className="form-row">
                {fields.slice(0, 2).map((field) => (
                  <Field key={field} field={field} values={values} setValues={setValues} errors={errors} required={required} />
                ))}
              </div>
              {fields.slice(2).map((field) => (
                <Field key={field} field={field} values={values} setValues={setValues} errors={errors} required={required} wide />
              ))}
              <button className="btn" type="submit">Submit</button>
            </form>
          )}
        </section>

        <section className="card contact-card">
          <h2>Visit Us</h2>
          <iframe
            className="map-frame"
            title={siteInfo.contact.google_maps_embed_query}
            src={`https://maps.google.com/maps?q=${mapQuery}&z=15&output=embed`}
            loading="lazy"
          />
          <ul className="visit-list">
            <li>
              <FaMapMarkerAlt />
              <span>{siteInfo.contact.full_address}</span>
            </li>
            {(siteInfo.contact.phones || []).map((phone) => (
              <li key={phone}>
                <FaPhoneAlt />
                <a href={`tel:${phone.replace(/\s/g, '')}`}>{phone}</a>
              </li>
            ))}
            {(siteInfo.contact.emails || []).map((email) => (
              <li key={email}>
                <FaEnvelope />
                <a href={`mailto:${email}`}>{email}</a>
              </li>
            ))}
          </ul>
        </section>
        <Sidebar title="Quick Links" links={links} />
      </div>
    </PageShell>
  );
}

function Field({ field, values, setValues, errors, required, wide }) {
  const multiline = /message|comment/i.test(field);
  const type = /email/i.test(field) ? 'email' : /phone/i.test(field) ? 'tel' : 'text';
  const input = multiline ? (
    <textarea
      rows={5}
      value={values[field] || ''}
      onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.value }))}
    />
  ) : (
    <input
      type={type}
      value={values[field] || ''}
      onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.value }))}
    />
  );

  return (
    <label style={wide ? undefined : undefined}>
      {field}{required.has(field) ? ' *' : ''}
      {input}
      {errors[field] && <span className="field-error">{errors[field]}</span>}
    </label>
  );
}
