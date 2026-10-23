import { Link, NavLink } from "react-router-dom";

import { useTheme } from "../theme";
import { CloverIcon, HistoryIcon, MoonIcon, SunIcon, WorkspaceIcon } from "./Icons";

const NAV = [
  { to: "/workspace", label: "创作工作台", icon: WorkspaceIcon, end: false },
  { to: "/history", label: "历史作品", icon: HistoryIcon, end: false },
];

export function Sidebar() {
  const { theme, toggle } = useTheme();

  return (
    <aside className="sidebar">
      <Link className="brand" to="/" title="回到首页">
        <span className="brand-mark"><CloverIcon />
        </span>
        <span className="brand-text">
          <strong>懂你所需</strong>
          <small>营销内容工作台</small>
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
