"use client";

import { useQuery } from "@tanstack/react-query";
import { useProjectStore } from "@/lib/project";
import { assetsApi } from "@/lib/api";
import { FolderOpen, LayoutTemplate } from "lucide-react";

export function Topbar() {
  const { project, assetId, setAssetId } = useProjectStore();

  const { data: assetsData } = useQuery({
    queryKey: ["assets", project?.id],
    queryFn: () => assetsApi.list(project?.id!).then((r) => r.data),
    enabled: !!project,
  });

  if (!project) return null;

  return (
    <header className="h-16 border-b border-gray-200 bg-white sticky top-0 z-10 w-full">
      <div className="w-full h-full flex items-center justify-between px-6">
        <div className="flex items-center gap-2">
          {/* Espacio para breadcrumbs si se requiere a futuro */}
        </div>
        
        <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <FolderOpen size={16} className="text-gray-400" />
          <span className="text-sm text-gray-500 font-medium">Proyecto:</span>
          <span className="text-sm font-semibold text-gray-900">{project.name}</span>
        </div>

        <div className="h-6 w-px bg-gray-200"></div>

        <div className="flex items-center gap-2">
          <LayoutTemplate size={16} className="text-gray-400" />
          <span className="text-sm text-gray-500 font-medium">Activo:</span>
          <select
            value={assetId}
            onChange={(e) => setAssetId(e.target.value)}
            className="bg-gray-50 border border-gray-200 text-gray-900 font-medium text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 min-w-[200px]"
          >
            <option value="all">Todos los activos</option>
            {assetsData?.items?.map((a: any) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        </div>
      </div>
    </header>
  );
}
