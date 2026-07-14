import { create } from "zustand";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  risk_appetite: string;
  business_context: string | null;
  status: string;
  asset_count: number;
  open_risk_count: number;
  critical_risk_count: number;
  created_at: string;
  updated_at: string;
}

interface ProjectStore {
  project: Project | null;
  assetId: string;
  _hasHydrated: boolean;
  setProject: (p: Project) => void;
  setAssetId: (id: string) => void;
  clearProject: () => void;
  hydrate: () => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  project: null,
  assetId: "all",
  _hasHydrated: false,
  setProject: (p) => {
    set((state) => {
      if (typeof window !== "undefined") {
        localStorage.setItem("wicscan-project", JSON.stringify(p));
      }
      const newAssetId = state.project?.id === p.id ? state.assetId : "all";
      return { project: p, assetId: newAssetId };
    });
  },
  setAssetId: (id) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("wicscan-asset", id);
    }
    set({ assetId: id });
  },
  clearProject: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("wicscan-project");
      localStorage.removeItem("wicscan-asset");
    }
    set({ project: null, assetId: "all" });
  },
  hydrate: () => {
    if (typeof window === "undefined") {
      set({ _hasHydrated: true });
      return;
    }
    try {
      const raw = localStorage.getItem("wicscan-project");
      const rawAsset = localStorage.getItem("wicscan-asset");
      set({ 
        project: raw ? JSON.parse(raw) : null, 
        assetId: rawAsset || "all",
        _hasHydrated: true 
      });
    } catch {
      set({ _hasHydrated: true });
    }
  },
}));
