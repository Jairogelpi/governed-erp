import type { ReactElement } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./Layout";
import { RequireAuth } from "./RequireAuth";
import { Overview } from "../screens/Overview";
import { Settings } from "../screens/Settings";
import { Connections } from "../screens/Connections";
import { Processes } from "../screens/Processes";
import { Replays } from "../screens/Replays";
import { Deployments } from "../screens/Deployments";
import { Opportunities } from "../screens/Opportunities";
import { Recommendations } from "../screens/Recommendations";
import { Canary } from "../screens/Canary";
import { Runs } from "../screens/Runs";
import { Outcomes } from "../screens/Outcomes";
import { Evidence } from "../screens/Evidence";
import { Benchmarks } from "../screens/Benchmarks";

function protect(element: ReactElement) {
  return <RequireAuth>{element}</RequireAuth>;
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={protect(<Overview />)} />
        <Route path="/connections" element={protect(<Connections />)} />
        <Route path="/processes" element={protect(<Processes />)} />
        <Route path="/replays" element={protect(<Replays />)} />
        <Route path="/deployments" element={protect(<Deployments />)} />
        <Route path="/opportunities" element={protect(<Opportunities />)} />
        <Route path="/recommendations" element={protect(<Recommendations />)} />
        <Route path="/canary" element={protect(<Canary />)} />
        <Route path="/runs" element={protect(<Runs />)} />
        <Route path="/outcomes" element={protect(<Outcomes />)} />
        <Route path="/evidence" element={protect(<Evidence />)} />
        <Route path="/benchmarks" element={protect(<Benchmarks />)} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
