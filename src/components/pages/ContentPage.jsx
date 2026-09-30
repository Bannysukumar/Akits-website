import { FaExternalLinkAlt } from 'react-icons/fa';
import PageShell from '../common/PageShell';
import ImageGallery from '../common/ImageGallery';
import DataTable from '../common/DataTable';
import DocumentLinks from '../common/DocumentLinks';
import {
  contentImages,
  decodeHtml,
  getSidebarLinks,
  isNavMirrorList,
  quickLinksHeading,
  resolveUrl,
  visibleHeadings,
} from '../../utils/helpers';

function RichText({ text, index }) {
  const decoded = decodeHtml(text);
  if (!decoded) return null;
  if ((decoded.match(/•/g) || []).length >= 2) {
    const parts = decoded.split('•').map((part) => part.trim()).filter(Boolean);
    return (
      <ul className="content-list" key={index}>
        {parts.map((part) => <li key={part}>{part}</li>)}
      </ul>
    );
  }
  return <p key={index}>{decoded}</p>;
}

function HeadingTag({ level, text }) {
  const tag = `h${Math.min(6, Math.max(2, Number(level) || 2))}`;
  const Tag = tag;
  return <Tag>{text}</Tag>;
}

function Media({ page }) {
  return (
    <>
      {(page.videos || []).map((video, index) => (
        <video key={`${video.src}-${index}`} controls src={resolveUrl(video.src)} poster={resolveUrl(video.poster)} />
      ))}
      {(page.iframes || []).map((frame, index) => (
        <iframe
          key={`${frame.src}-${index}`}
          className="embed-frame"
          src={resolveUrl(frame.src)}
          title={decodeHtml(frame.title) || decodeHtml(page.title)}
        />
      ))}
      <DocumentLinks documents={page.documents} />
    </>
  );
}

export default function ContentPage({ page, variant = 'default' }) {
  const sidebar = getSidebarLinks(page.route);
  const sidebarTitle = quickLinksHeading(page);
  const headings = visibleHeadings(page);
  const images = contentImages(page);
  const lists = (page.lists || []).filter((list) => !isNavMirrorList(list, sidebar));
  const paragraphs = page.paragraphs || [];
  const hasBody = paragraphs.length || images.length || page.tables?.length || lists.length || page.documents?.length || page.videos?.length;

  if (variant === 'hod') {
    const profileTitle = headings.find((heading) => /hod profile/i.test(heading.text));
    const rest = headings.filter((heading) => heading !== profileTitle);
    const name = rest.find((heading) => heading.level <= 2);
    const qualification = rest.find((heading) => heading !== name);

    return (
      <PageShell page={page} links={sidebar} sidebarTitle={sidebarTitle}>
        <h1>{decodeHtml(page.title)}</h1>
        <div className="hod-layout">
          <div className="prose">
            {profileTitle && <h2>{profileTitle.text}</h2>}
            {paragraphs.map((text, index) => <RichText key={index} text={text} index={index} />)}
            {lists.map((list, index) => (
              <ListBlock key={index} list={list} />
            ))}
          </div>
          <div className="hod-card">
            {images[0] && <img src={resolveUrl(images[0].src)} alt={name?.text || decodeHtml(page.title)} />}
            {name && <h3>{name.text}</h3>}
            {qualification && <p>{qualification.text}</p>}
          </div>
        </div>
        {(page.tables || []).map((table, index) => (
          <DataTable key={index} headers={table.headers} rows={table.rows} />
        ))}
        {images.length > 1 && <ImageGallery images={images.slice(1)} />}
        <Media page={page} />
      </PageShell>
    );
  }

  return (
    <PageShell page={page} links={sidebar} sidebarTitle={sidebarTitle}>
      <h1>{decodeHtml(page.title)}</h1>
      <div className="prose">
        {headings.map((heading, index) => (
          <HeadingTag key={`${heading.text}-${index}`} level={heading.level} text={heading.text} />
        ))}
        {paragraphs.map((text, index) => <RichText key={index} text={text} index={index} />)}
        {lists.map((list, index) => <ListBlock key={index} list={list} />)}
      </div>
      {(page.tables || []).map((table, index) => (
        <DataTable key={index} headers={table.headers} rows={table.rows} />
      ))}
      <ImageGallery images={images} />
      <Media page={page} />
      {!hasBody && page.external_url && (
        <p>
          <a className="btn" href={page.external_url} target="_blank" rel="noreferrer">
            <FaExternalLinkAlt /> Open {decodeHtml(page.title)}
          </a>
        </p>
      )}
    </PageShell>
  );
}

function ListBlock({ list }) {
  const Tag = list.type === 'ordered' ? 'ol' : 'ul';
  return (
    <Tag className="content-list">
      {list.items.map((item) => (
        <li key={item}>{decodeHtml(item)}</li>
      ))}
    </Tag>
  );
}
