import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import {
  LayoutGrid,
  BriefcaseBusiness,
  GraduationCap,
  ShieldCheck,
  UserRound,
  Sparkles,
  ArrowUpRight,
  ChevronDown,
  Menu,
  X,
  LogOut,
} from "lucide-react";
import { AuthProvider, useAuth } from "./lib/api";
import { AccessGate, Empty } from "./components/ui";
import Catalog from "./pages/Catalog";
import Login from "./pages/Login";
import ProblemDetail from "./pages/ProblemDetail";
import CompanyDashboard from "./pages/CompanyDashboard";
import ProblemEditor from "./pages/ProblemEditor";
import StudentDashboard from "./pages/StudentDashboard";
import StudentProfile from "./pages/StudentProfile";
import SubmitProject from "./pages/SubmitProject";
import Review from "./pages/Review";
import Admin from "./pages/Admin";
import "./styles.css";

function App() {
  const { user, logout } = useAuth();
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  const current = location.pathname.startsWith("/company")
    ? "Пространство бизнеса"
    : location.pathname.startsWith("/student")
      ? "Пространство студента"
      : location.pathname.startsWith("/admin")
        ? "Модерация"
        : location.pathname.startsWith("/problems")
          ? "Бизнес-задача"
          : location.pathname === "/login"
            ? "Демо-вход"
            : "Каталог задач";
  const roleName =
    user?.role === "STUDENT"
      ? "Студент"
      : user?.role === "COMPANY"
        ? "Компания"
        : "Администратор";
  return (
    <div className="app">
      <aside className={`sidebar ${menu ? "mobile-open" : ""}`}>
        <Link className="brand" to="/" onClick={() => setMenu(false)}>
          <span className="brand-mark">
            <Sparkles size={25} />
          </span>
          <span>
            ai sana<span className="brand-dot">.</span>
          </span>
        </Link>
        <span className="sidebar-caption">ПРОСТРАНСТВО ВОЗМОЖНОСТЕЙ</span>
        <nav aria-label="Основная навигация" onClick={() => setMenu(false)}>
          <NavLink to="/" end>
            <LayoutGrid size={19} />
            Каталог задач
          </NavLink>
          <div className="nav-label">МОЙ КАБИНЕТ</div>
          <NavLink to="/student/dashboard">
            <GraduationCap size={20} />
            Студентам
          </NavLink>
          <NavLink to="/company/dashboard">
            <BriefcaseBusiness size={19} />
            Бизнесу
          </NavLink>
          {user?.role === "STUDENT" && (
            <NavLink to="/student/profile">
              <UserRound size={19} />
              Мой профиль
            </NavLink>
          )}
          {user?.role === "ADMIN" && (
            <NavLink to="/admin">
              <ShieldCheck size={19} />
              Модерация
            </NavLink>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <Sparkles size={21} />
            <strong>От задачи к опыту</strong>
            <p>
              Работайте с реальным бизнесом. Создавайте то, что имеет значение.
            </p>
          </div>
          <div className="sidebar-footer">
            <span className="status-light" /> DEMO WORKSPACE <span>v1.0</span>
          </div>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-backdrop"
          aria-label="Закрыть меню"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="app-main">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label={menu ? "Закрыть меню" : "Открыть меню"}
            onClick={() => setMenu(!menu)}
          >
            {menu ? <X size={22} /> : <Menu size={22} />}
          </button>
          <div className="breadcrumb">
            <span>Платформа</span>
            <span>/</span>
            <strong>{current}</strong>
          </div>
          <div className="topbar-right">
            <span className="demo-label">Демо-режим</span>
            {user ? (
              <>
                <Link to="/login" className="account-button">
                  <span className="account-avatar">
                    {user.name.slice(0, 1)}
                  </span>
                  <span>
                    <strong>{user.name}</strong>
                    <small>{roleName}</small>
                  </span>
                  <ChevronDown size={16} />
                </Link>
                <button
                  className="icon-button logout"
                  aria-label="Выйти"
                  onClick={logout}
                >
                  <LogOut size={17} />
                </button>
              </>
            ) : (
              <Link className="button compact" to="/login">
                Демо-вход <ArrowUpRight size={16} />
              </Link>
            )}
          </div>
        </header>
        <main key={user?.id ?? "guest"}>
          <Routes>
            <Route path="/" element={<Catalog />} />
            <Route path="/login" element={<Login />} />
            <Route path="/problems/:id" element={<ProblemDetail />} />
            <Route
              path="/company/dashboard"
              element={
                <AccessGate role="COMPANY">
                  <CompanyDashboard />
                </AccessGate>
              }
            />
            <Route
              path="/company/problems/new"
              element={
                <AccessGate role="COMPANY">
                  <ProblemEditor />
                </AccessGate>
              }
            />
            <Route
              path="/company/problems/:id/edit"
              element={
                <AccessGate role="COMPANY">
                  <ProblemEditor />
                </AccessGate>
              }
            />
            <Route
              path="/company/problems/:id/submissions"
              element={
                <AccessGate role="COMPANY">
                  <Review />
                </AccessGate>
              }
            />
            <Route
              path="/student/dashboard"
              element={
                <AccessGate role="STUDENT">
                  <StudentDashboard />
                </AccessGate>
              }
            />
            <Route
              path="/student/profile"
              element={
                <AccessGate role="STUDENT">
                  <StudentProfile />
                </AccessGate>
              }
            />
            <Route
              path="/student/problems/:id/submit"
              element={
                <AccessGate role="STUDENT">
                  <SubmitProject />
                </AccessGate>
              }
            />
            <Route
              path="/admin"
              element={
                <AccessGate role="ADMIN">
                  <Admin />
                </AccessGate>
              }
            />
            <Route
              path="*"
              element={
                <Empty title="Страница не найдена">
                  <Link className="button" to="/">
                    В каталог
                  </Link>
                </Empty>
              }
            />
          </Routes>
        </main>
        <footer className="page-footer">
          <span>AI Sana · Бизнес и новое поколение создателей</span>
          <span>Реальные задачи. Осмысленный опыт.</span>
        </footer>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
