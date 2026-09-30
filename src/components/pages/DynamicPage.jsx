import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Spinner from '../common/Spinner';
import ContentPage from './ContentPage';
import DepartmentPage from './DepartmentPage';
import GalleryPage from './GalleryPage';
import NotFoundPage from './NotFoundPage';
import {
  buildPhotoGalleryPage,
  contentImages,
  getPage,
  isDepartmentPath,
  isGalleryPath,
  normalizePath,
  syntheticPage,
} from '../../utils/helpers';

export default function DynamicPage() {
  const { pathname } = useLocation();
  const path = normalizePath(pathname);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => setLoading(false), 180);
    return () => clearTimeout(timer);
  }, [path]);

  if (loading) return <Spinner />;

  if (path === '/gallery/photo-gallery') {
    const existing = getPage(path);
    const page = existing && contentImages(existing).length > 1 ? existing : buildPhotoGalleryPage();
    return <GalleryPage page={page} />;
  }

  if (isGalleryPath(path)) {
    const page = getPage(path);
    if (page) return <GalleryPage page={page} />;
  }

  if (isDepartmentPath(path)) {
    const page = getPage(path) || syntheticPage(path);
    if (page) return <DepartmentPage page={page} />;
  }

  const page = getPage(path);
  if (page) return <ContentPage page={page} />;

  const fallback = syntheticPage(path);
  if (fallback) return <ContentPage page={fallback} />;

  return <NotFoundPage />;
}
