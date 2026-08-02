import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getToken } from "../api/client";

export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (!getToken()) {
    return <Navigate to="/settings" state={{ from: location, reason: "auth_required" }} replace />;
  }
  return <>{children}</>;
}
