import { NavLink, Outlet } from "react-router-dom";
import { NAV_ITEMS } from "./nav";

export function Layout() {
  return (
    <div className="app-shell">
      <nav className="app-nav">
        <h1>ERPGuard</h1>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
