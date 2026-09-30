import { BrowserRouter, Route, Routes } from 'react-router-dom';
import OriginalChrome from './components/Layout/OriginalChrome';
import OriginalPage from './components/pages/OriginalPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<OriginalChrome />}>
          <Route path="*" element={<OriginalPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
