import { useEffect } from "react";
import { TopBar } from "./components/TopBar/TopBar";
import { PassPanel } from "./components/PassPanel/PassPanel";
import { SpectrumPanel } from "./components/SpectrumPanel/SpectrumPanel";
import { LinkBudgetPanel } from "./components/LinkBudgetPanel/LinkBudgetPanel";
import { PassHistory } from "./components/PassHistory/PassHistory";
import { useWebSocket } from "./hooks/useWebSocket";
import { useStore } from "./store";
import { api } from "./services/api";

function App() {
  useWebSocket();

  const setSdrStatus = useStore((s) => s.setSdrStatus);

  useEffect(() => {
    api.getSdrStatus().then(setSdrStatus).catch(() => {});
  }, [setSdrStatus]);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar />

      <div className="flex-1 grid grid-cols-[240px_1fr_260px] gap-2 p-2 overflow-hidden">
        {/* Left panel */}
        <PassPanel />

        {/* Center panel */}
        <SpectrumPanel />

        {/* Right panel */}
        <LinkBudgetPanel />
      </div>

      {/* Bottom panel */}
      <div className="p-2 pt-0">
        <PassHistory />
      </div>
    </div>
  );
}

export default App;
