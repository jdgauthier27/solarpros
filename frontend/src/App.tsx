import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./components/Dashboard/Dashboard";
import PropertyMap from "./components/PropertyMap/PropertyMap";
import ProspectTable from "./components/ProspectTable/ProspectTable";
import CampaignManager from "./components/CampaignManager/CampaignManager";
import AgentStatus from "./components/AgentStatus/AgentStatus";
import OutreachQueues from "./components/OutreachQueues/OutreachQueues";
import TakeoffUpload from "./components/TakeoffUpload/TakeoffUpload";
import SheetBrowser from "./components/SheetBrowser/SheetBrowser";

const navItems = [
  { to: "/", label: "Dashboard", icon: "\u2302" },
  { to: "/properties", label: "Properties", icon: "\u2630" },
  { to: "/map", label: "Map", icon: "\u25CB" },
  { to: "/campaigns", label: "Campaigns", icon: "\u2709" },
  { to: "/outreach", label: "Outreach", icon: "\u260E" },
  { to: "/agents", label: "Agents", icon: "\u2699" },
  { to: "/takeoff", label: "Takeoff", icon: "\u2702" },
];

const sidebarStyle: React.CSSProperties = {
  width: 220,
  minHeight: "100vh",
  background: "#1a1a2e",
  color: "#eee",
  display: "flex",
  flexDirection: "column",
  padding: "20px 0",
  position: "fixed",
  left: 0,
  top: 0,
};

const logoStyle: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 700,
  padding: "0 20px 24px",
  borderBottom: "1px solid #333",
  marginBottom: 12,
  color: "#f9a825",
};

const linkStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "12px 20px",
  color: "#bbb",
  textDecoration: "none",
  fontSize: 15,
  transition: "background 0.15s, color 0.15s",
};

const activeLinkStyle: React.CSSProperties = {
  ...linkStyle,
  color: "#fff",
  background: "rgba(249, 168, 37, 0.15)",
  borderRight: "3px solid #f9a825",
};

const mainStyle: React.CSSProperties = {
  marginLeft: 220,
  padding: "24px 32px",
  background: "#f5f5f5",
  minHeight: "100vh",
};

export default function App() {
  return (
    <div style={{ display: "flex" }}>
      <nav style={sidebarStyle}>
        <div style={logoStyle}>SolarPros</div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            style={({ isActive }) => (isActive ? activeLinkStyle : linkStyle)}
          >
            <span style={{ fontSize: 18 }}>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main style={mainStyle}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/properties" element={<ProspectTable />} />
          <Route path="/map" element={<PropertyMap />} />
          <Route path="/campaigns" element={<CampaignManager />} />
          <Route path="/outreach" element={<OutreachQueues />} />
          <Route path="/agents" element={<AgentStatus />} />
          <Route path="/takeoff" element={<TakeoffUpload />} />
          <Route path="/takeoff/:projectId" element={<SheetBrowser />} />
        </Routes>
      </main>
    </div>
  );
}
