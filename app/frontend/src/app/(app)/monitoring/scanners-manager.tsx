"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scannersApi } from "@/lib/api";
import { ShieldAlert, Database, Plus, Edit2, Trash2, Bot, Crosshair, type LucideIcon } from "lucide-react";

const ENGINE_ICON: Record<string, LucideIcon> = {
  sonarqube: Database,
  nuclei:    Crosshair,
  AI_REVIEW: Bot,
};
const ENGINE_COLOR: Record<string, string> = {
  sonarqube: "text-blue-500",
  nuclei:    "text-purple-500",
  AI_REVIEW: "text-green-500",
};

export function ScannersManager() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    name: "",
    engine_type: "sonarqube",
    category: "sast",
    url: "",
    api_key: "",
    is_active: true
  });

  const { data: scanners, isLoading } = useQuery({
    queryKey: ["scanners"],
    queryFn: () => scannersApi.list().then(res => res.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => scannersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scanners"] });
      setIsModalOpen(false);
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string, data: any }) => scannersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scanners"] });
      setIsModalOpen(false);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => scannersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scanners"] });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const openEdit = (scanner: any) => {
    setFormData({
      name: scanner.name,
      engine_type: scanner.engine_type,
      category: scanner.category || "sast",
      url: scanner.url,
      api_key: scanner.api_key || "",
      is_active: scanner.is_active
    });
    setEditingId(scanner.id);
    setIsModalOpen(true);
  };

  const openNew = () => {
    setFormData({
      name: "",
      engine_type: "sonarqube",
      category: "sast",
      url: "",
      api_key: "",
      is_active: true
    });
    setEditingId(null);
    setIsModalOpen(true);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <ShieldAlert size={16} className="text-gray-400" />
          Motores de Escaneo (Scanners)
        </h2>
        <button 
          onClick={openNew}
          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5"
        >
          <Plus size={14} /> Registrar Escáner
        </button>
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-500">Cargando escáneres...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scanners?.length === 0 && (
            <div className="col-span-full text-sm text-gray-500 italic">No hay escáneres registrados.</div>
          )}
          {scanners?.map((scanner: any) => (
            <div key={scanner.id} className="border border-gray-200 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-gray-900 font-medium">
                    {(() => {
                    const Icon  = ENGINE_ICON[scanner.engine_type]  ?? ShieldAlert;
                    const color = ENGINE_COLOR[scanner.engine_type] ?? "text-orange-500";
                    return <Icon size={16} className={color} />;
                  })()}
                    {scanner.name}
                  </div>
                  <div className={`text-xs font-semibold rounded-full px-2 py-0.5 inline-flex items-center gap-1 ${
                    scanner.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {scanner.is_active ? "Activo" : "Inactivo"}
                  </div>
                </div>
                <div className="text-xs text-gray-500 mb-1">
                  <span className="font-semibold">Tipo:</span> <span className="uppercase">{scanner.engine_type}</span>
                  <span className="mx-2 text-gray-300">|</span>
                  <span className="font-semibold">Cat:</span> <span className="uppercase">{scanner.category}</span>
                </div>
                <div className="text-xs text-gray-500 truncate" title={scanner.url}>
                  <span className="font-semibold">URL:</span> {scanner.url}
                </div>
              </div>
              
              <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-gray-100">
                <button onClick={() => openEdit(scanner)} className="text-gray-400 hover:text-blue-600">
                  <Edit2 size={16} />
                </button>
                <button 
                  onClick={() => {
                    if (confirm("¿Estás seguro de eliminar este escáner?")) {
                      deleteMutation.mutate(scanner.id);
                    }
                  }} 
                  className="text-gray-400 hover:text-red-600"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl">
            <h3 className="text-lg font-bold mb-4">{editingId ? "Editar Escáner" : "Registrar Nuevo Escáner"}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input 
                  required
                  type="text" 
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm"
                  placeholder="Ej: SonarQube Principal"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motor (Tipo)</label>
                <input 
                  required
                  type="text"
                  list="engineTypes"
                  value={formData.engine_type}
                  onChange={e => setFormData({...formData, engine_type: e.target.value.toLowerCase()})}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm"
                  placeholder="Ej: sonarqube, zap, trivy..."
                />
                <datalist id="engineTypes">
                  <option value="mobsf">MobSF</option>
                  <option value="sonarqube">SonarQube</option>
                  <option value="zap">OWASP ZAP</option>
                  <option value="nuclei">Nuclei</option>
                  <option value="ai_review">Scanner IA</option>
                </datalist>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
                <select
                  required
                  value={formData.category}
                  onChange={e => setFormData({...formData, category: e.target.value})}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm bg-white"
                >
                  <option value="sast">SAST (Análisis Estático)</option>
                  <option value="dast">DAST (Análisis Dinámico)</option>
                  <option value="sca">SCA (Dependencias)</option>
                  <option value="ia">IA (Revisión de IA)</option>
                  <option value="vuln">Gestión de Vulnerabilidades</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
                <input 
                  required
                  type="text" 
                  value={formData.url}
                  onChange={e => setFormData({...formData, url: e.target.value})}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm"
                  placeholder="Ej: http://sonarqube:9000 o local"
                />
                <p className="text-[10px] text-gray-500 mt-1">
                  Nota: En entornos Docker, usa el nombre del contenedor (ej. <code className="bg-gray-100 px-1 rounded">http://zap:8080</code>) en lugar de <code className="bg-gray-100 px-1 rounded">127.0.0.1</code>.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key / Token (Opcional)</label>
                <input 
                  type="password" 
                  autoComplete="current-password"
                  value={formData.api_key}
                  onChange={e => setFormData({...formData, api_key: e.target.value})}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm"
                  placeholder="Deja vacío si no usa autenticación"
                />
              </div>
              <div className="flex items-center gap-2 mt-2">
                <input 
                  type="checkbox" 
                  id="isActive"
                  checked={formData.is_active}
                  onChange={e => setFormData({...formData, is_active: e.target.checked})}
                />
                <label htmlFor="isActive" className="text-sm font-medium text-gray-700">Escáner Activo</label>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancelar
                </button>
                <button 
                  type="submit" 
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
                >
                  {createMutation.isPending || updateMutation.isPending ? "Guardando..." : "Guardar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
