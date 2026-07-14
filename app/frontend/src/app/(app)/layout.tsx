"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { useAuthStore } from "@/lib/auth";
import { useProjectStore } from "@/lib/project";
import { projectsApi } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, user, loadUser, _hasHydrated: authHydrated, hydrate: hydrateAuth } = useAuthStore();
  const { project, _hasHydrated, hydrate, clearProject } = useProjectStore();

  // Hydrate both stores from localStorage after mount.
  // This must happen in useEffect (not during render) so the initial
  // server render and client render both see null state — no hydration mismatch.
  useEffect(() => {
    hydrateAuth();
    hydrate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auth + routing guard — runs once both stores have hydrated
  useEffect(() => {
    if (!authHydrated || !_hasHydrated) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!user) {
      loadUser().catch(() => router.replace("/login"));
    }
    if (!project && pathname !== "/projects") {
      router.replace("/projects");
    }
  }, [token, user, project, _hasHydrated, authHydrated, pathname, router, loadUser]);

  // Auto-detect stale project: verify it still exists on the backend.
  // If the DB was wiped and re-seeded, the stored project ID is invalid.
  useEffect(() => {
    if (!authHydrated || !token || !project) return;
    projectsApi.get(project.id).catch((err) => {
      if (err.response?.status === 404) {
        clearProject();
      }
    });
  }, [authHydrated, token, project?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Don't render anything until auth has hydrated — this keeps
  // the initial client render identical to the server render (both null).
  if (!authHydrated) return null;
  if (!token) return null;

  return (
    <div className="flex min-h-screen bg-gray-200/50 justify-center">
      <div className="flex w-full max-w-[1400px] bg-white min-h-screen shadow-lg border-x border-gray-200">
        <Sidebar />
        <main className="flex-1 bg-gray-50 flex flex-col min-w-0">
          <Topbar />
          <div className="p-6 w-full">{children}</div>
        </main>
      </div>
    </div>
  );
}
