import ContentPage from './ContentPage';
import { isHodPath } from '../../utils/helpers';

export default function DepartmentPage({ page }) {
  return <ContentPage page={page} variant={isHodPath(page.route) ? 'hod' : 'department'} />;
}
