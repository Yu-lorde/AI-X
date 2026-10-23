import { Link, NavLink } from "react-router-dom";

import { useTheme } from "../theme";
import { HistoryIcon, MoonIcon, SunIcon, WorkspaceIcon } from "./Icons";

const NAV = [
  { to: "/workspace", label: "创作工作台", icon: WorkspaceIcon, end: false },
  { to: "/history", label: "历史作品", icon: HistoryIcon, end: false },
];

export function Sidebar() {
  const { theme, toggle } = useTheme();

  return (
    <aside className="sidebar">
      <Link className="brand" to="/" title="回到首页">
        <span className="brand-mark">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path d="M12 2.6l2.1 5.7 5.7 2.1-5.7 2.1L12 18.2l-2.1-5.7L4.2 10.4l5.7-2.1z" />
          </svg>
        </span>
        <span className="brand-text">
          <strong>AI+X</strong>
          <small>营销软文工作台</small>
        </span>
      </Link>

      <nav className="nav">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <button type="button" className="theme-toggle" onClick={toggle} title="切换日间 / 夜间">
          {theme === "light" ? <MoonIcon size={16} /> : <SunIcon size={16} />}
          <span>{theme === "light" ? "夜间模式" : "日间模式"}</span>
        </button>
        <p className="sidebar-hint">历史仅保存在当前浏览器，数据落在本机 SQLite。</p>
      </div>
    </aside>
  );
}
