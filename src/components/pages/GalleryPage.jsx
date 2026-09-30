import PageShell from '../common/PageShell';
import ImageGallery from '../common/ImageGallery';
import DocumentLinks from '../common/DocumentLinks';
import {
  contentImages,
  decodeHtml,
  getSidebarLinks,
  quickLinksHeading,
  resolveUrl,
} from '../../utils/helpers';

export default function GalleryPage({ page }) {
  const images = contentImages(page);
  const videos = page.videos || [];
  const sidebar = getSidebarLinks(page.route);

  return (
    <PageShell page={page} links={sidebar} sidebarTitle={quickLinksHeading(page)}>
      <h1>{decodeHtml(page.title)}</h1>
      {(page.paragraphs || []).map((text) => <p key={text}>{decodeHtml(text)}</p>)}
      {videos.length > 0 && (
        <div className="video-grid">
          {videos.map((video, index) => (
            <video key={`${video.src}-${index}`} controls preload="metadata" src={resolveUrl(video.src)} poster={resolveUrl(video.poster)} />
          ))}
        </div>
      )}
      <ImageGallery images={images} />
      <DocumentLinks documents={page.documents} />
    </PageShell>
  );
}
