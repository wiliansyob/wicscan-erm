"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  catalogApi,
  type DefinitionOut,
  type QuestionDefinitionOut,
  type QuestionDefinitionIn,
} from "@/lib/api/admin";
import {
  ArrowLeft, CheckCircle, Loader, AlertTriangle, Plus, Trash2,
  Save, Send, LibraryBig, Lock, Edit3, X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const BLOCK_LABELS: Record<string, string> = {
  A: "A — Normativa y perfil",
  B: "B — Perfil organizativo",
  C: "C — Datos y tratamiento",
  D: "D — Sector específico",
};

const TYPE_LABELS: Record<string, string> = {
  single_choice: "Selección única",
  multi_choice: "Selección múltiple",
  free_text: "Texto libre",
  range: "Rango / Escala",
};

// ─── Question form modal ──────────────────────────────────────────────────────

interface QuestionFormData {
  question_id: string;
  block: string;
  text: string;
  type: QuestionDefinitionIn["type"];
  options_raw: string;
  order: number;
  feeds_raw: string;
}

function emptyForm(block: string): QuestionFormData {
  return { question_id: "", block, text: "", type: "single_choice", options_raw: "", order: 0, feeds_raw: "" };
}

function formFromQuestion(q: QuestionDefinitionOut): QuestionFormData {
  return {
    question_id: q.question_id,
    block: q.block,
    text: q.text,
    type: q.type,
    options_raw: (q.options ?? []).join("\n"),
    order: q.order,
    feeds_raw: (q.feeds ?? []).join(", "),
  };
}

function formToIn(f: QuestionFormData): QuestionDefinitionIn {
  const opts = f.options_raw
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const feeds = f.feeds_raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return {
    block: f.block,
    text: f.text,
    type: f.type,
    options: opts.length > 0 ? opts : null,
    order: f.order,
    feeds: feeds.length > 0 ? feeds : null,
  };
}

interface QuestionModalProps {
  definitionId: string;
  initialData: QuestionFormData;
  isEditing: boolean;
  onClose: () => void;
}

function QuestionModal({ definitionId, initialData, isEditing, onClose }: QuestionModalProps) {
  const qc = useQueryClient();
  const [form, setForm] = useState<QuestionFormData>(initialData);
  const [error, setError] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () =>
      catalogApi.upsertQuestion(definitionId, form.question_id, formToIn(form)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questionnaire-definition", definitionId] });
      onClose();
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail ?? "Error al guardar la pregunta.");
    },
  });

  const set = (field: keyof QuestionFormData, value: unknown) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const needsOptions = form.type === "single_choice" || form.type === "multi_choice";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-bold text-gray-900">
            {isEditing ? "Editar pregunta" : "Nueva pregunta"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          {/* ID + Block */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">ID de pregunta</label>
              <input
                type="text"
                value={form.question_id}
                onChange={(e) => set("question_id", e.target.value)}
                disabled={isEditing}
                placeholder="Ej. A1, B2a…"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Bloque</label>
              <select
                value={form.block}
                onChange={(e) => set("block", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                {["A", "B", "C", "D"].map((b) => (
                  <option key={b} value={b}>
                    Bloque {b}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Text */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Texto de la pregunta</label>
            <textarea
              rows={3}
              value={form.text}
              onChange={(e) => set("text", e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          {/* Type + Order */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Tipo de respuesta</label>
              <select
                value={form.type}
                onChange={(e) => set("type", e.target.value as QuestionDefinitionIn["type"])}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                {Object.entries(TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Orden</label>
              <input
                type="number"
                value={form.order}
                onChange={(e) => set("order", Number(e.target.value))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Options */}
          {needsOptions && (
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">
                Opciones <span className="text-gray-400 font-normal">(una por línea — el valor es la cadena exacta)</span>
              </label>
              <textarea
                rows={4}
                value={form.options_raw}
                onChange={(e) => set("options_raw", e.target.value)}
                placeholder={"Sí\nNo\nNo aplica"}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none font-mono"
              />
            </div>
          )}

          {/* Feeds */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">
              Campos que alimenta <span className="text-gray-400 font-normal">(separados por coma, opcional)</span>
            </label>
            <input
              type="text"
              value={form.feeds_raw}
              onChange={(e) => set("feeds_raw", e.target.value)}
              placeholder="rgpd_applies, nis2_status"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
              <AlertTriangle size={13} className="flex-shrink-0" />
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-700 font-medium px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !form.question_id.trim() || !form.text.trim()}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2 px-5 transition-all"
          >
            {saveMutation.isPending ? <Loader size={13} className="animate-spin" /> : <Save size={13} />}
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function QuestionnaireEditorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [activeBlock, setActiveBlock] = useState("A");
  const [modal, setModal] = useState<{ open: boolean; form: QuestionFormData; isEditing: boolean } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const { data: def, isLoading, isError } = useQuery<DefinitionOut>({
    queryKey: ["questionnaire-definition", id],
    queryFn: () => catalogApi.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const deleteMutation = useMutation({
    mutationFn: (questionId: string) => catalogApi.deleteQuestion(id, questionId),
    onSuccess: () => {
      setActionSuccess("Pregunta eliminada.");
      qc.invalidateQueries({ queryKey: ["questionnaire-definition", id] });
    },
    onError: (err: any) => setActionError(err?.response?.data?.detail ?? "Error al eliminar."),
  });

  const validateMutation = useMutation({
    mutationFn: () => catalogApi.validate(id),
    onSuccess: (res) => {
      if (res.data.valid) {
        setActionSuccess("Validación correcta: el árbol de preguntas es coherente.");
        setActionError(null);
      } else {
        setActionError("Validación fallida: " + res.data.errors.join(" · "));
        setActionSuccess(null);
      }
    },
    onError: (err: any) => setActionError(err?.response?.data?.detail ?? "Error al validar."),
  });

  const publishMutation = useMutation({
    mutationFn: () => catalogApi.publish(id),
    onSuccess: () => {
      setActionSuccess("¡Versión publicada! Ya está disponible para nuevos cuestionarios.");
      setActionError(null);
      qc.invalidateQueries({ queryKey: ["questionnaire-definition", id] });
      qc.invalidateQueries({ queryKey: ["questionnaire-definitions"] });
    },
    onError: (err: any) => setActionError(err?.response?.data?.detail ?? "Error al publicar."),
  });

  const isDraft = def?.status === "draft";
  const blockQuestions = def?.questions.filter((q) => q.block === activeBlock) ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 gap-3 text-gray-500">
        <Loader size={18} className="animate-spin text-blue-600" />
        <span className="text-sm">Cargando definición…</span>
      </div>
    );
  }

  if (isError || !def) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <AlertTriangle size={15} />
          No se pudo cargar la definición. Verifica el ID y la conexión con el backend.
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {modal && (
        <QuestionModal
          definitionId={id}
          initialData={modal.form}
          isEditing={modal.isEditing}
          onClose={() => setModal(null)}
        />
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button
            onClick={() => router.push("/admin/questionnaire")}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-700 mb-2 transition-colors"
          >
            <ArrowLeft size={12} /> Catálogo
          </button>
          <div className="flex items-center gap-2">
            <LibraryBig size={18} className="text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">
              {def.version != null ? `Versión v${def.version}` : "Borrador sin publicar"}
            </h1>
            <span className={cn(
              "text-xs font-semibold px-2 py-0.5 rounded-full",
              def.status === "published" ? "bg-green-100 text-green-700" :
              def.status === "draft" ? "bg-yellow-100 text-yellow-700" :
              "bg-gray-100 text-gray-500"
            )}>
              {def.status === "published" ? "Publicada" : def.status === "draft" ? "Borrador" : "Archivada"}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {def.questions.length} preguntas · {def.dependencies.length} dependencias
            {def.notes && <> · {def.notes}</>}
          </p>
        </div>

        {/* Actions for drafts */}
        {isDraft && (
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
              className="flex items-center gap-2 border border-gray-300 hover:border-gray-400 text-gray-700 hover:text-gray-900 text-sm font-medium rounded-xl py-2.5 px-4 transition-all disabled:opacity-50"
            >
              {validateMutation.isPending ? <Loader size={13} className="animate-spin" /> : <CheckCircle size={13} />}
              Validar
            </button>
            <button
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 px-5 transition-all"
            >
              {publishMutation.isPending ? <Loader size={13} className="animate-spin" /> : <Send size={13} />}
              Publicar
            </button>
          </div>
        )}

        {!isDraft && (
          <div className="flex items-center gap-2 text-sm text-gray-400 flex-shrink-0">
            <Lock size={14} />
            <span>Versión inmutable</span>
          </div>
        )}
      </div>

      {/* Feedback banners */}
      {actionSuccess && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
          <CheckCircle size={15} className="flex-shrink-0" />
          {actionSuccess}
          <button onClick={() => setActionSuccess(null)} className="ml-auto text-green-500 hover:text-green-700">
            <X size={14} />
          </button>
        </div>
      )}
      {actionError && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <AlertTriangle size={15} className="flex-shrink-0" />
          {actionError}
          <button onClick={() => setActionError(null)} className="ml-auto text-red-400 hover:text-red-600">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Block tabs */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="border-b border-gray-100 flex">
          {["A", "B", "C", "D"].map((b) => {
            const count = def.questions.filter((q) => q.block === b).length;
            return (
              <button
                key={b}
                onClick={() => setActiveBlock(b)}
                className={cn(
                  "flex-1 py-3 px-4 text-sm font-medium transition-colors border-b-2 text-center",
                  activeBlock === b
                    ? "border-blue-600 text-blue-700 bg-blue-50/40"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                )}
              >
                <span className="block text-xs font-bold">Bloque {b}</span>
                <span className="text-[10px] text-gray-400">{count} preg.</span>
              </button>
            );
          })}
        </div>

        {/* Block header */}
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-700">{BLOCK_LABELS[activeBlock]}</p>
            <p className="text-xs text-gray-400 mt-0.5">{blockQuestions.length} preguntas en este bloque</p>
          </div>
          {isDraft && (
            <button
              onClick={() =>
                setModal({ open: true, form: emptyForm(activeBlock), isEditing: false })
              }
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-semibold px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors"
            >
              <Plus size={12} /> Añadir pregunta
            </button>
          )}
        </div>

        {/* Questions list */}
        {blockQuestions.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-gray-400">Sin preguntas en este bloque.</p>
            {isDraft && (
              <button
                onClick={() =>
                  setModal({ open: true, form: emptyForm(activeBlock), isEditing: false })
                }
                className="mt-3 inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                <Plus size={11} /> Añadir la primera pregunta
              </button>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {blockQuestions
              .sort((a, b) => a.order - b.order)
              .map((q) => (
                <li key={q.question_id} className="px-5 py-4 flex items-start gap-4 hover:bg-gray-50 transition-colors group">
                  {/* ID badge */}
                  <span className="text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-100 px-2 py-1 rounded mt-0.5 flex-shrink-0 font-mono">
                    {q.question_id}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 leading-snug">{q.text}</p>
                    <div className="flex items-center flex-wrap gap-2 mt-1.5">
                      <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        {TYPE_LABELS[q.type]}
                      </span>
                      {q.options && q.options.length > 0 && (
                        <span className="text-[10px] text-gray-400">
                          {q.options.slice(0, 3).join(" · ")}
                          {q.options.length > 3 && ` +${q.options.length - 3}`}
                        </span>
                      )}
                      {q.feeds && q.feeds.length > 0 && (
                        <span className="text-[10px] text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded">
                          feeds: {q.feeds.join(", ")}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  {isDraft && (
                    <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() =>
                          setModal({ open: true, form: formFromQuestion(q), isEditing: true })
                        }
                        className="p-1.5 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                        title="Editar"
                      >
                        <Edit3 size={14} />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`¿Eliminar la pregunta ${q.question_id}?`)) {
                            deleteMutation.mutate(q.question_id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="p-1.5 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                        title="Eliminar"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  )}
                </li>
              ))}
          </ul>
        )}
      </div>

      {/* Dependencies summary */}
      {def.dependencies.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-3.5 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-700">Dependencias condicionales</p>
            <p className="text-xs text-gray-400 mt-0.5">
              Una pregunta hija solo se muestra si se cumple la condición del padre.
            </p>
          </div>
          <ul className="divide-y divide-gray-100">
            {def.dependencies.map((dep) => (
              <li key={dep.id} className="px-5 py-3 text-xs text-gray-600 flex items-center gap-2 flex-wrap">
                <span className="font-mono font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                  {dep.parent_question_id}
                </span>
                <span className="text-gray-400">= «{dep.trigger_value}»</span>
                <span className="text-gray-400">→ muestra</span>
                {dep.child_question_id && (
                  <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">
                    {dep.child_question_id}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
