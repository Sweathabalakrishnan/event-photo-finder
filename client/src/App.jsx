import { Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import Admin from "./pages/Admin";
import EventPage from "./pages/EventPage";
import Gallery from "./pages/Gallery";
import "./styles.css";

export default function App() {
  return (
    <div className="appShell">
      <header className="navbar">
        <div className="container navbarInner">
          <Link to="/" className="brand">
            <div className="brandBadge">AI</div>
            <span>Event Photo Finder</span>
          </Link>

          <nav className="navLinks">
            <Link className="navLink" to="/">Home</Link>
            <Link className="navLink" to="/admin">Admin</Link>
          </nav>
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/event/:eventCode" element={<EventPage />} />
          <Route path="/gallery" element={<Gallery />} />
        </Routes>
      </main>

      <div className="footerSpace" />
    </div>
  );
}