"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Eye, EyeOff, Loader } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuthStore();

  const [form, setForm] = useState({
    workspace_name: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authApi.register(form);
      await login(form.email, form.password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Error al crear la cuenta");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/20">
            <ShieldAlert size={20} className="text-white" />
          </div>
          <div>
            <p className="text-gray-900 font-bold text-lg leading-none">WicScan</p>
            <p className="text-gray-500 text-xs">Risk Manager</p>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
          <h1 className="text-xl font-bold text-gray-900 mb-1">Crear cuenta</h1>
          <p className="text-gray-500 text-sm mb-6">Configura tu workspace</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Nombre del workspace</label>
              <input
                type="text"
                value={form.workspace_name}
                onChange={set("workspace_name")}
                required
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all placeholder-gray-400"
                placeholder="Acme Corp"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Nombre completo</label>
              <input
                type="text"
                value={form.full_name}
                onChange={set("full_name")}
                required
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all placeholder-gray-400"
                placeholder="Ana García"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Correo electrónico</label>
              <input
                type="email"
                value={form.email}
                onChange={set("email")}
                required
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all placeholder-gray-400"
                placeholder="tu@ejemplo.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Contraseña</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={set("password")}
                  required
                  minLength={8}
                  className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm pr-10 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all"
                  placeholder="Mín. 8 caracteres"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 text-xs rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-lg py-2.5 text-sm transition-all flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <Loader size={14} className="animate-spin" />
                  Creando cuenta…
                </>
              ) : (
                "Crear cuenta"
              )}
            </button>
          </form>

          <p className="text-center text-xs text-gray-500 mt-6">
            ¿Ya tienes cuenta?{" "}
            <a href="/login" className="text-blue-600 hover:text-blue-700 transition-colors font-medium">
              Inicia sesión
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
