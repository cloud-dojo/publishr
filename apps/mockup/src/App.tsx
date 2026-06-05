import { Routes, Route } from "react-router-dom";
import StorefrontPage from "./pages/StorefrontPage";
import LibraryPage from "./pages/LibraryPage";
import BookDetailPage from "./pages/BookDetailPage";
import WritingPage from "./pages/WritingPage";
import ReaderPage from "./pages/ReaderPage";
import HighlightsPage from "./pages/HighlightsPage";
import AuthorPage from "./pages/AuthorPage";
import AuthorsPage from "./pages/AuthorsPage";
import AppMapPage from "./pages/AppMapPage";
import LoginPage from "./pages/LoginPage";
import OnboardingPage from "./pages/OnboardingPage";
import ConnectPage from "./pages/ConnectPage";
import AccountPage from "./pages/AccountPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/connect" element={<ConnectPage />} />
      <Route path="/" element={<StorefrontPage />} />
      <Route path="/library" element={<LibraryPage />} />
      <Route path="/book/:bookId" element={<BookDetailPage />} />
      <Route path="/writing/:bookId" element={<WritingPage />} />
      <Route path="/reader/:bookId" element={<ReaderPage />} />
      <Route path="/highlights" element={<HighlightsPage />} />
      <Route path="/authors" element={<AuthorsPage />} />
      <Route path="/author/:personaId" element={<AuthorPage />} />
      <Route path="/account" element={<AccountPage />} />
      <Route path="/map" element={<AppMapPage />} />
    </Routes>
  );
}
