import { api } from "@/lib/api";

const PREFIX = "/admin/questionnaire-definitions";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface QuestionDefinitionOut {
  id: string;
  definition_id: string;
  question_id: string;
  block: string;
  text: string;
  type: "single_choice" | "multi_choice" | "range" | "free_text";
  options?: string[] | null;
  order: number;
  feeds?: string[] | null;
}

export interface QuestionDefinitionIn {
  block: string;
  text: string;
  type: "single_choice" | "multi_choice" | "range" | "free_text";
  options?: string[] | null;
  order?: number;
  feeds?: string[] | null;
}

export interface QuestionDependencyOut {
  id: string;
  definition_id: string;
  parent_question_id: string;
  trigger_value: string;
  child_question_id?: string | null;
  effect?: string | null;
}

export interface QuestionDependencyIn {
  parent_question_id: string;
  trigger_value: string;
  child_question_id?: string | null;
  effect?: string | null;
}

export interface DefinitionOut {
  id: string;
  version: number;
  status: "draft" | "published" | "archived";
  published_at?: string | null;
  notes?: string | null;
  created_at: string;
  questions: QuestionDefinitionOut[];
  dependencies: QuestionDependencyOut[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export interface PublishResult {
  id: string;
  version: number;
  status: string;
  published_at: string;
}

// ─── API client ───────────────────────────────────────────────────────────────

export const catalogApi = {
  list: () =>
    api.get<DefinitionOut[]>(PREFIX),

  get: (definitionId: string) =>
    api.get<DefinitionOut>(`${PREFIX}/${definitionId}`),

  create: (notes?: string) =>
    api.post<DefinitionOut>(PREFIX, { notes }),

  upsertQuestion: (definitionId: string, questionId: string, data: QuestionDefinitionIn) =>
    api.put<QuestionDefinitionOut>(`${PREFIX}/${definitionId}/questions/${questionId}`, data),

  deleteQuestion: (definitionId: string, questionId: string) =>
    api.delete(`${PREFIX}/${definitionId}/questions/${questionId}`),

  addDependency: (definitionId: string, data: QuestionDependencyIn) =>
    api.post<QuestionDependencyOut>(`${PREFIX}/${definitionId}/dependencies`, data),

  removeDependency: (definitionId: string, depId: string) =>
    api.delete(`${PREFIX}/${definitionId}/dependencies/${depId}`),

  validate: (definitionId: string) =>
    api.post<ValidationResult>(`${PREFIX}/${definitionId}/validate`),

  publish: (definitionId: string) =>
    api.post<PublishResult>(`${PREFIX}/${definitionId}/publish`),

  archive: (definitionId: string) =>
    api.post<DefinitionOut>(`${PREFIX}/${definitionId}/archive`),

  deleteDraft: (definitionId: string) =>
    api.delete(`${PREFIX}/${definitionId}`),
};
