import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";

declare global {
  interface Window {
    katex?: {
      renderToString: (tex: string, options?: Record<string, unknown>) => string;
    };
    renderMathInElement?: (element: HTMLElement, options?: Record<string, unknown>) => void;
  }
}

interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  subject?: string | null;
  grade?: string | null;
  year?: number | null;
  school?: string | null;
  upload_status: string;
  processing_status: string;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

interface QuestionOption {
  label: string;
  text: string;
}

interface SubQuestion {
  qno?: string;
  question_type?: string | null;
  answer?: string | null;
  knowledge_points?: string[];
  score?: number | null;
}

interface ReviewDecision {
  status: "pending" | "approved" | "rejected";
  comment?: string;
  updated_at?: string;
}

interface ReviewOverride {
  [key: string]: unknown;
}

interface IngestSummary {
  total?: number;
  ingested?: number;
  discarded?: number;
  discard_reasons?: Record<string, number>;
}

interface QuestionImageRef {
  question_number: string;
  image_id: string;
  placement?: string;
}

interface ImageAsset {
  image_id: string;
  page_no?: number | null;
  bbox?: {
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
  } | null;
  source?: string | null;
  figure_id?: string | null;
  placement?: string | null;
  url?: string | null;
  xref?: number | null;
}

type ReviewFilter =
  | "all"
  | "pending"
  | "approved"
  | "rejected"
  | "needs_review"
  | "discarded"
  | "composite"
  | "answers_missing";

interface CorrectedAnchor {
  field: string;
  llm_line_ids: string[];
  corrected_line_ids: string[];
  anchor_status: string;
  validation_passed?: boolean;
  evidence?: string | null;
}

interface Provenance {
  field?: string;
  source?: string;
  confidence?: number;
  evidence?: string;
}

interface Question {
  question_number?: string;
  question_type?: string;
  section_id?: string | null;
  stem: string;
  options: QuestionOption[];
  answer?: string | null;
  explanation?: string | null;
  difficulty?: number | null;
  score?: number | null;
  knowledge_points?: string[];
  confidence?: number;
  source_page?: number | null;
  stem_line_ids?: string[];
  options_line_ids?: Record<string, string[]>;
  answer_line_ids?: string[];
  explanation_line_ids?: string[];
  answer_provenance?: Provenance | null;
  explanation_provenance?: Provenance | null;
  corrected_anchors?: CorrectedAnchor[];
  is_composite?: boolean;
  sub_questions?: SubQuestion[] | null;
  shared_material_line_ids?: string[];
  shared_material?: string;
  review_notes?: string[];
  discard_categories?: string[];
  discard_details?: string[];
  issues?: string[];
}

interface PipelineStage {
  name: string;
  duration_ms: number;
  [key: string]: unknown;
}

interface ParseResult {
  status?: string;
  stages?: PipelineStage[];
  stage_errors?: string[];
  total_time_ms?: number;
  errors?: string[];
  question_count?: number;
  questions?: Question[];
  ingested_questions?: Question[];
  discarded_questions?: Question[];
  ingest_summary?: IngestSummary;
  images?: ImageAsset[];
  question_images?: QuestionImageRef[];
  review_decisions?: Record<string, ReviewDecision>;
  review_overrides?: Record<string, ReviewOverride>;
  _label?: string;
  _elapsed_s?: number;
}

interface ParseResponse {
  task_id?: string | null;
  document_id?: string;
  status?: string;
  progress?: number | null;
  current_stage?: string | null;
  error_message?: string | null;
  result?: ParseResult | null;
}

interface ApiEnvelope<T> {
  data: T;
}

interface QuestionDraft {
  question_type: string;
  section_id: string;
  stem: string;
  options: QuestionOption[];
  answer: string;
  explanation: string;
  difficulty: number | null;
  score: number | null;
  knowledge_points: string[];
}

const TYPE_LABELS: Record<string, string> = {
  single_choice: "单选",
  multiple_choice: "多选",
  fill_in: "填空",
  true_false: "判断",
  short_answer: "解答",
  cloze: "完形",
  reading: "阅读",
  grammar_fill: "语法填空",
  vocabulary_fill: "词汇填空",
  seven_to_five: "七选五",
  reading_expression: "阅读表达",
  essay: "写作",
  文言文: "文言文",
  材料: "材料",
  工艺流程: "工艺流程",
  实验: "实验",
};

const TYPE_OPTIONS = [
  "single_choice",
  "multiple_choice",
  "fill_in",
  "true_false",
  "short_answer",
  "cloze",
  "reading",
  "grammar_fill",
  "vocabulary_fill",
  "seven_to_five",
  "reading_expression",
  "essay",
  "文言文",
  "材料",
  "工艺流程",
  "实验",
];

const REVIEW_LABELS: Record<ReviewDecision["status"], string> = {
  pending: "待定",
  approved: "通过",
  rejected: "驳回",
};

const FILTER_LABELS: Record<ReviewFilter, string> = {
  all: "全部",
  pending: "待定",
  approved: "已通过",
  rejected: "已驳回",
  needs_review: "需审核",
  discarded: "已丢弃",
  composite: "综合题",
  answers_missing: "缺答案",
};

function confidenceLevel(confidence?: number) {
  if (confidence === undefined) {
    return "low";
  }
  if (confidence >= 0.8) {
    return "high";
  }
  if (confidence >= 0.6) {
    return "medium";
  }
  return "low";
}

function questionKey(question: Question, index: number) {
  return question.question_number?.trim() || `unlabeled-${index + 1}`;
}

function asString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback: number | null = null) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : fallback;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}

function asOptions(value: unknown, fallback: QuestionOption[] = []) {
  if (!Array.isArray(value)) {
    return fallback;
  }
  return value
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      label: asString(item.label, "A"),
      text: asString(item.text, ""),
    }))
    .filter((option) => option.text.trim() !== "");
}

function asStringArray(value: unknown, fallback: string[] = []) {
  if (!Array.isArray(value)) {
    return fallback;
  }
  return value.map(String).filter((item) => item.trim() !== "");
}

function draftFromQuestion(question: Question, override?: ReviewOverride): QuestionDraft {
  return {
    question_type: asString(override?.question_type, question.question_type ?? ""),
    section_id: asString(override?.section_id, question.section_id ?? ""),
    stem: asString(override?.stem, question.stem ?? ""),
    options: asOptions(override?.options, question.options ?? []),
    answer: asString(override?.answer, question.answer ?? ""),
    explanation: asString(override?.explanation, question.explanation ?? ""),
    difficulty: asNumber(override?.difficulty, question.difficulty ?? null),
    score: asNumber(override?.score, question.score ?? null),
    knowledge_points: asStringArray(override?.knowledge_points, question.knowledge_points ?? []),
  };
}

function effectiveQuestion(question: Question, override?: ReviewOverride): Question {
  if (!override) {
    return question;
  }
  return {
    ...question,
    question_type: asString(override.question_type, question.question_type ?? ""),
    section_id: asString(override.section_id, question.section_id ?? ""),
    stem: asString(override.stem, question.stem ?? ""),
    options: asOptions(override.options, question.options ?? []),
    answer: asString(override.answer, question.answer ?? ""),
    explanation: asString(override.explanation, question.explanation ?? ""),
    difficulty: asNumber(override.difficulty, question.difficulty ?? null),
    score: asNumber(override.score, question.score ?? null),
    knowledge_points: asStringArray(override.knowledge_points, question.knowledge_points ?? []),
  };
}

function overrideFromDraft(draft: QuestionDraft): ReviewOverride {
  return {
    question_type: draft.question_type,
    section_id: draft.section_id,
    stem: draft.stem,
    options: draft.options,
    answer: draft.answer,
    explanation: draft.explanation,
    difficulty: draft.difficulty,
    score: draft.score,
    knowledge_points: draft.knowledge_points,
  };
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderLatexText(value: string) {
  const katex = window.katex;
  if (!katex) {
    return escapeHtml(value);
  }
  const parts = value.split(/(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g);
  return parts
    .map((part) => {
      if (part.startsWith("$$") && part.endsWith("$$") && part.length > 4) {
        try {
          return katex.renderToString(part.slice(2, -2), {
            displayMode: true,
            throwOnError: false,
          });
        } catch {
          return escapeHtml(part);
        }
      }
      if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
        try {
          return katex.renderToString(part.slice(1, -1), {
            displayMode: false,
            throwOnError: false,
          });
        } catch {
          return escapeHtml(part);
        }
      }
      return escapeHtml(part);
    })
    .join("");
}

function MathText({ text, className = "" }: { text: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }
    delete node.dataset.mathReady;
    node.textContent = text;

    const render = () => {
      if (node.dataset.mathReady) {
        return;
      }
      if (window.renderMathInElement) {
        window.renderMathInElement(node, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\[", right: "\\]", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\(", right: "\\)", display: false },
          ],
          throwOnError: false,
        });
        node.dataset.mathReady = "1";
      } else if (window.katex) {
        node.innerHTML = renderLatexText(text);
        node.dataset.mathReady = "1";
      } else {
        node.textContent = text;
      }
    };

    render();
    const timer = window.setTimeout(render, 800);
    return () => window.clearTimeout(timer);
  }, [text]);

  return (
    <div ref={ref} className={`math-content ${className}`}>
      {text}
    </div>
  );
}

function QuestionImages({ images }: { images: ImageAsset[] }) {
  if (images.length === 0) {
    return null;
  }
  return (
    <div className="question-image-block">
      <strong>配图</strong>
      <div className="question-image-grid">
        {images.map((image) => (
          <figure className="question-image" key={image.image_id}>
            {image.url ? (
              <img
                src={image.url}
                alt={`${image.placement ?? "题目"}配图 ${image.image_id}`}
                loading="lazy"
                onError={(event) => {
                  event.currentTarget.hidden = true;
                  event.currentTarget.nextElementSibling?.classList.add("visible");
                }}
              />
            ) : (
              <span className="image-fallback visible">无图片地址</span>
            )}
            <figcaption>
              {image.image_id}
              {image.placement ? ` / ${image.placement}` : ""}
              {image.page_no ? ` / 第${image.page_no}页` : ""}
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

function isDiscarded(question: Question) {
  return Boolean(
    question.discard_categories?.length ||
      question.discard_details?.length ||
      (question.confidence ?? 1) < 0.8 ||
      !question.stem?.trim() ||
      !question.answer?.trim(),
  );
}

function isReviewRequired(question: Question) {
  return Boolean(
    question.review_notes?.length ||
      question.discard_categories?.length ||
      question.discard_details?.length ||
      question.issues?.length ||
      (question.confidence ?? 1) < 0.8 ||
      !question.stem?.trim() ||
      !question.answer?.trim(),
  );
}

function summarize(result?: ParseResult | null) {
  const questions = result?.questions ?? [];
  const decisions = result?.review_decisions ?? {};
  const overrides = result?.review_overrides ?? {};
  const summary = {
    high: 0,
    medium: 0,
    low: 0,
    blocked: 0,
    answerMatched: 0,
    answerEmpty: 0,
    composite: 0,
    subQuestions: 0,
    needsReview: 0,
    pending: 0,
    approved: 0,
    rejected: 0,
    discarded: 0,
  };
  for (let index = 0; index < questions.length; index += 1) {
    const original = questions[index];
    const key = questionKey(original, index);
    const question = effectiveQuestion(original, overrides[key]);
    const level = confidenceLevel(question.confidence);
    summary[level] += 1;
    const issues = question.issues ?? [];
    if (issues.some((issue) => issue.includes("禁止自动发布"))) {
      summary.blocked += 1;
    }
    if (question.answer?.trim()) {
      summary.answerMatched += 1;
    } else {
      summary.answerEmpty += 1;
    }
    if (question.is_composite) {
      summary.composite += 1;
    }
    summary.subQuestions += question.sub_questions?.length ?? 0;
    if (isDiscarded(question)) {
      summary.discarded += 1;
    }
    if (isReviewRequired(question)) {
      const decision = decisions[key];
      if (!decision || decision.status === "pending") {
        summary.needsReview += 1;
      }
    }
    const decision = decisions[key];
    if (decision?.status === "pending") {
      summary.pending += 1;
    } else if (decision?.status === "approved") {
      summary.approved += 1;
    } else if (decision?.status === "rejected") {
      summary.rejected += 1;
    }
  }
  return summary;
}

function anchorMap(question: Question) {
  return new Map(
    (question.corrected_anchors ?? []).map((anchor) => [anchor.field, anchor]),
  );
}

function matchesFilter(question: Question, decision: ReviewDecision | undefined, filter: ReviewFilter) {
  if (filter === "all") {
    return true;
  }
  if (filter === "pending") {
    return !decision || decision.status === "pending";
  }
  if (filter === "approved") {
    return decision?.status === "approved";
  }
  if (filter === "rejected") {
    return decision?.status === "rejected";
  }
  if (filter === "needs_review") {
    return isReviewRequired(question);
  }
  if (filter === "discarded") {
    return isDiscarded(question);
  }
  if (filter === "composite") {
    return Boolean(question.is_composite || question.sub_questions?.length);
  }
  if (filter === "answers_missing") {
    return !question.answer?.trim();
  }
  return true;
}

interface QuestionCardProps {
  question: Question;
  index: number;
  decision?: ReviewDecision;
  override?: ReviewOverride;
  images?: ImageAsset[];
  displayOnly?: boolean;
  canSaveToBackend: boolean;
  saving?: boolean;
  onSave: (status: ReviewDecision["status"], comment: string, overrides?: ReviewOverride) => Promise<void>;
}

function QuestionCard({
  question,
  index,
  decision,
  override,
  images = [],
  displayOnly = false,
  canSaveToBackend,
  saving,
  onSave,
}: QuestionCardProps) {
  const key = questionKey(question, index);
  const [comment, setComment] = useState(decision?.comment ?? "");
  const [draft, setDraft] = useState<QuestionDraft>(() => draftFromQuestion(question, override));
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const effective = effectiveQuestion(question, override);
  const level = confidenceLevel(effective.confidence);
  const issues = effective.issues ?? [];
  const blocked = issues.some((issue) => issue.includes("禁止自动发布"));
  const anchors = anchorMap(effective);
  const hasOverride = Boolean(override && Object.keys(override).length > 0);

  async function submitDecision(status: ReviewDecision["status"]) {
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await onSave(status, comment, hasOverride ? override : undefined);
      setMessage(REVIEW_LABELS[status]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function saveDraft() {
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await onSave(decision?.status ?? "pending", comment, overrideFromDraft(draft));
      setMessage("修正已保存");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSubmitting(false);
    }
  }

  function updateDraft(patch: Partial<QuestionDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function updateOption(indexToUpdate: number, patch: Partial<QuestionOption>) {
    setDraft((current) => ({
      ...current,
      options: current.options.map((option, optionIndex) =>
        optionIndex === indexToUpdate ? { ...option, ...patch } : option,
      ),
    }));
  }

  return (
    <article className={`question-card ${blocked ? "is-blocked" : ""} ${hasOverride ? "has-override" : ""}`}>
      <div className="question-card-header">
        <div className="question-title">
          <strong>{key}</strong>
          <span>{TYPE_LABELS[effective.question_type ?? ""] ?? effective.question_type ?? "未知题型"}</span>
          {effective.section_id ? <span>{effective.section_id}</span> : null}
          {effective.is_composite ? <span>综合题</span> : null}
        </div>
        <div className="badge-row">
          <span className={`badge badge-${level}`}>{level}</span>
          {blocked ? <span className="badge badge-blocked">blocked</span> : null}
          {isDiscarded(effective) ? <span className="badge badge-discarded">丢弃候选</span> : null}
          <span>置信度 {(effective.confidence ?? 0).toFixed(2)}</span>
          {decision ? (
            <span className={`review-state review-${decision.status}`}>{REVIEW_LABELS[decision.status]}</span>
          ) : (
            <span className="review-state review-pending">未审</span>
          )}
          {hasOverride ? <span className="badge badge-override">已修正</span> : null}
        </div>
      </div>

      {!displayOnly ? (
        <>
          <div className="review-controls">
            <input
              className="review-comment-input"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="审核意见"
              aria-label={`${key} 审核意见`}
            />
            <button
              className="decision-button approve"
              type="button"
              disabled={!canSaveToBackend || submitting || saving}
              onClick={() => void submitDecision("approved")}
            >
              通过
            </button>
            <button
              className="decision-button reject"
              type="button"
              disabled={!canSaveToBackend || submitting || saving}
              onClick={() => void submitDecision("rejected")}
            >
              驳回
            </button>
            <button
              className="decision-button pending"
              type="button"
              disabled={!canSaveToBackend || submitting || saving}
              onClick={() => void submitDecision("pending")}
            >
              待定
            </button>
            {!canSaveToBackend ? <span className="inline-muted">缺少题号，不能保存审核</span> : null}
          </div>

          {message ? <div className="inline-success">{message}</div> : null}
          {error ? <div className="inline-error">{error}</div> : null}
        </>
      ) : null}

      <div className="question-content">
        {effective.stem ? (
          <MathText className="stem-text" text={effective.stem} />
        ) : (
          <p className="muted">（题干为空）</p>
        )}
        {effective.options.length > 0 ? (
          <ol className="option-list">
            {effective.options.map((option) => (
              <li key={option.label}>
                <strong>{option.label}.</strong> <MathText text={option.text} />
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted">无选项</p>
        )}

        <QuestionImages images={images} />

        {effective.shared_material ? (
          <div className="shared-material">
            <strong>共享材料</strong>
            <MathText text={effective.shared_material} />
          </div>
        ) : null}

        {effective.sub_questions?.length ? (
          <div className="subquestion-list">
            <strong>子题</strong>
            {effective.sub_questions.map((sub, subIndex) => (
              <div key={sub.qno ?? subIndex} className="subquestion-row">
                <span>{sub.qno ?? `子题 ${subIndex + 1}`}</span>
                <span>{TYPE_LABELS[sub.question_type ?? ""] ?? sub.question_type ?? ""}</span>
                <span>
                  <MathText text={sub.answer || "缺答案"} />
                </span>
              </div>
            ))}
          </div>
        ) : null}

        <dl className="answer-grid">
          <div>
            <dt>答案</dt>
            <dd>
              <MathText text={effective.answer || "未匹配"} />
            </dd>
          </div>
          <div>
            <dt>答案来源</dt>
            <dd>{effective.answer_provenance?.source || "未知"}</dd>
          </div>
          <div>
            <dt>页码</dt>
            <dd>{effective.source_page ?? "未知"}</dd>
          </div>
          <div>
            <dt>锚点</dt>
            <dd>
              {anchors.get("stem")?.anchor_status ?? "无"}
              {effective.stem_line_ids?.length ? ` / ${effective.stem_line_ids.join(", ")}` : ""}
            </dd>
          </div>
        </dl>

        {effective.explanation ? (
          <div className="explanation-block">
            <strong>详解</strong>
            <MathText text={effective.explanation} />
          </div>
        ) : null}

        {effective.review_notes?.length ? (
          <ul className="issue-list review-note-list">
            {effective.review_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        ) : null}

        {issues.length > 0 ? (
          <ul className="issue-list">
            {issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        ) : null}

        {effective.discard_categories?.length || effective.discard_details?.length ? (
          <div className="discard-block">
            <strong>丢弃原因</strong>
            <p>{effective.discard_categories?.join(" / ") || "未分类"}</p>
            {effective.discard_details?.length ? (
              <ul>
                {effective.discard_details.map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>

      {!displayOnly ? (
        <>
      <div className="edit-panel">
        <button
          className="text-button"
          type="button"
          onClick={() => setEditing((current) => !current)}
          aria-expanded={editing}
        >
          {editing ? "收起修正" : "修正内容"}
        </button>
        {editing ? (
          <div className="edit-grid">
            <label className="edit-field">
              <span>题型</span>
              <select value={draft.question_type} onChange={(event) => updateDraft({ question_type: event.target.value })}>
                <option value="">未知题型</option>
                {TYPE_OPTIONS.map((type) => (
                  <option key={type} value={type}>
                    {TYPE_LABELS[type] ?? type}
                  </option>
                ))}
              </select>
            </label>
            <label className="edit-field">
              <span>章节</span>
              <input value={draft.section_id} onChange={(event) => updateDraft({ section_id: event.target.value })} />
            </label>
            <label className="edit-field">
              <span>难度</span>
              <input
                type="number"
                min={1}
                max={5}
                value={draft.difficulty ?? ""}
                onChange={(event) =>
                  updateDraft({ difficulty: event.target.value === "" ? null : Number(event.target.value) })
                }
              />
            </label>
            <label className="edit-field">
              <span>分值</span>
              <input
                type="number"
                min={0}
                value={draft.score ?? ""}
                onChange={(event) =>
                  updateDraft({ score: event.target.value === "" ? null : Number(event.target.value) })
                }
              />
            </label>
            <label className="edit-field wide">
              <span>知识点（逗号分隔）</span>
              <input
                value={draft.knowledge_points.join(", ")}
                onChange={(event) =>
                  updateDraft({
                    knowledge_points: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
                  })
                }
              />
            </label>
            <label className="edit-field wide">
              <span>题干</span>
              <textarea value={draft.stem} onChange={(event) => updateDraft({ stem: event.target.value })} rows={4} />
            </label>
            <div className="edit-field wide">
              <span>选项</span>
              <div className="option-editor">
                {draft.options.length === 0 ? <p className="muted">暂无选项</p> : null}
                {draft.options.map((option, optionIndex) => (
                  <div className="option-editor-row" key={`${option.label}-${optionIndex}`}>
                    <input
                      className="option-label-input"
                      value={option.label}
                      onChange={(event) => updateOption(optionIndex, { label: event.target.value })}
                      aria-label="选项标签"
                    />
                    <textarea
                      value={option.text}
                      onChange={(event) => updateOption(optionIndex, { text: event.target.value })}
                      rows={2}
                      aria-label="选项内容"
                    />
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() =>
                        setDraft((current) => ({
                          ...current,
                          options: current.options.filter((_, currentIndex) => currentIndex !== optionIndex),
                        }))
                      }
                      aria-label="删除选项"
                    >
                      ×
                    </button>
                  </div>
                ))}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    setDraft((current) => ({
                      ...current,
                      options: [...current.options, { label: String.fromCharCode(65 + current.options.length), text: "" }],
                    }))
                  }
                >
                  添加选项
                </button>
              </div>
            </div>
            <label className="edit-field wide">
              <span>答案</span>
              <textarea value={draft.answer} onChange={(event) => updateDraft({ answer: event.target.value })} rows={2} />
            </label>
            <label className="edit-field wide">
              <span>详解</span>
              <textarea
                value={draft.explanation}
                onChange={(event) => updateDraft({ explanation: event.target.value })}
                rows={5}
              />
            </label>
            <div className="edit-actions">
              <button
                className="primary-button"
                type="button"
                disabled={!canSaveToBackend || submitting || saving}
                onClick={() => void saveDraft()}
              >
                保存修正
              </button>
              {hasOverride ? (
                <button
                  className="secondary-button"
                  type="button"
                  disabled={submitting || saving}
                  onClick={() => {
                    setDraft(draftFromQuestion(question, {}));
                    void onSave(decision?.status ?? "pending", comment, {})
                      .then(() => setMessage("修正已清除"))
                      .catch((caught) => setError(caught instanceof Error ? caught.message : String(caught)));
                  }}
                >
                  清除修正
                </button>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      <details className="raw-details">
        <summary>行号审计</summary>
        <pre>
          {JSON.stringify(
            {
              stem_line_ids: effective.stem_line_ids,
              options_line_ids: effective.options_line_ids,
              answer_line_ids: effective.answer_line_ids,
              explanation_line_ids: effective.explanation_line_ids,
              corrected_anchors: effective.corrected_anchors,
              answer_provenance: effective.answer_provenance,
              explanation_provenance: effective.explanation_provenance,
            },
            null,
            2,
          )}
        </pre>
      </details>
        </>
      ) : null}
    </article>
  );
}

export default function AdminHome() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [parse, setParse] = useState<ParseResponse | null>(null);
  const [importedResult, setImportedResult] = useState<ParseResult | null>(null);
  const [importedVersion, setImportedVersion] = useState(0);
  const [localDecisions, setLocalDecisions] = useState<Record<string, ReviewDecision>>({});
  const [localOverrides, setLocalOverrides] = useState<Record<string, ReviewOverride>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReviewFilter>("all");
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [viewMode, setViewMode] = useState<"display" | "review">("display");
  const [copied, setCopied] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);

  const selectedDocument = documents.find((document) => document.id === selectedId) ?? null;
  const result = useMemo(() => {
    const base = importedResult ?? parse?.result ?? null;
    if (!base) {
      return null;
    }
    return {
      ...base,
      review_decisions: {
        ...(base.review_decisions ?? {}),
        ...localDecisions,
      },
      review_overrides: {
        ...(base.review_overrides ?? {}),
        ...localOverrides,
      },
    };
  }, [importedResult, parse, localDecisions, localOverrides]);
  const summary = useMemo(() => summarize(result), [result]);
  const imagesByQuestion = useMemo(() => {
    const byId = new Map<string, ImageAsset>((result?.images ?? []).map((image) => [image.image_id, image]));
    const grouped = new Map<string, ImageAsset[]>();
    for (const ref of result?.question_images ?? []) {
      const asset = byId.get(ref.image_id);
      if (asset?.url) {
        const list = grouped.get(ref.question_number) ?? [];
        list.push({
          ...asset,
          placement: ref.placement ?? asset.placement ?? null,
        });
        grouped.set(ref.question_number, list);
      }
    }
    return grouped;
  }, [result]);

  useEffect(() => {
    void fetchDocuments();
  }, []);

  useEffect(() => {
    setLocalDecisions({});
    setLocalOverrides({});
  }, [selectedId, importedResult]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let active = true;

    async function loadParse() {
      try {
        const response = await fetch(`/api/admin/documents/${selectedId}/parse-result`);
        if (!response.ok) {
          throw new Error(`解析接口返回 ${response.status}`);
        }
        const body = (await response.json()) as ApiEnvelope<ParseResponse>;
        if (active) {
          setParse(body.data);
        }
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : String(caught));
        }
      }
    }

    void loadParse();
    const timer = window.setInterval(loadParse, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [selectedId]);

  async function fetchDocuments() {
    setError(null);
    try {
      const response = await fetch("/api/admin/documents?page_size=100");
      if (!response.ok) {
        throw new Error(`文档接口返回 ${response.status}`);
      }
      const body = (await response.json()) as ApiEnvelope<{
        items: DocumentItem[];
        total: number;
      }>;
      setDocuments(body.data.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = fileRef.current;
    if (!input?.files?.length) {
      return;
    }

    const formData = new FormData();
    for (const file of Array.from(input.files)) {
      formData.append("files", file);
    }
    const subject = (document.getElementById("subject") as HTMLInputElement | null)?.value;
    const grade = (document.getElementById("grade") as HTMLInputElement | null)?.value;
    const year = (document.getElementById("year") as HTMLInputElement | null)?.value;
    if (subject) {
      formData.append("subject", subject);
    }
    if (grade) {
      formData.append("grade", grade);
    }
    if (year) {
      formData.append("year", year);
    }

    setUploading(true);
    setError(null);
    setUploadMessage(null);
    try {
      const response = await fetch("/api/admin/documents/upload", {
        method: "POST",
        body: formData,
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(body?.error?.message ?? `上传接口返回 ${response.status}`);
      }
      const data = body.data as { document_ids: string[] };
      setUploadMessage(`已排队 ${data.document_ids.length} 份文档`);
      input.value = "";
      await fetchDocuments();
      if (data.document_ids[0]) {
        setImportedResult(null);
        setParse(null);
        setSelectedId(data.document_ids[0]);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setUploading(false);
    }
  }

  async function handleImport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const text = await file.text();
      const data = JSON.parse(text) as ParseResult;
      if (!Array.isArray(data.questions)) {
        throw new Error("JSON 中缺少 questions 数组");
      }
      setImportedResult(data);
      setImportedVersion((current) => current + 1);
      setParse(null);
      setSelectedId(null);
      setLocalDecisions({});
      setLocalOverrides({});
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      event.target.value = "";
    }
  }

  async function saveReview(
    question: Question,
    index: number,
    status: ReviewDecision["status"],
    comment: string,
    overrides?: ReviewOverride,
  ) {
    const key = questionKey(question, index);
    if (!question.question_number?.trim()) {
      throw new Error("题目缺少 question_number，不能保存");
    }
    setSavingKey(key);
    setError(null);
    try {
      if (!selectedId) {
        const decision: ReviewDecision = {
          status,
          comment,
          updated_at: new Date().toISOString(),
        };
        setLocalDecisions((current) => ({ ...current, [key]: decision }));
        if (overrides !== undefined) {
          setLocalOverrides((current) => ({ ...current, [key]: overrides }));
        }
        return;
      }

      const response = await fetch(`/api/admin/documents/${selectedId}/review`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_number: question.question_number,
          status,
          comment,
          overrides,
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(body?.error?.message ?? `审核接口返回 ${response.status}`);
      }
      const data = body.data as {
        status: ReviewDecision["status"];
        comment: string;
        updated_at: string;
        overrides?: ReviewOverride;
      };
      setLocalDecisions((current) => ({
        ...current,
        [key]: {
          status: data.status,
          comment: data.comment,
          updated_at: data.updated_at,
        },
      }));
      const savedOverride = data.overrides;
      if (savedOverride !== undefined) {
        setLocalOverrides((current) => ({ ...current, [key]: savedOverride }));
      }
    } finally {
      setSavingKey(null);
    }
  }

  async function copyResult() {
    if (!result || !navigator.clipboard) {
      return;
    }
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  function exportResult() {
    if (!result) {
      return;
    }
    const exportData = {
      ...result,
      review_decisions: result.review_decisions ?? {},
      review_overrides: result.review_overrides ?? {},
      _review_exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `review_${selectedDocument?.filename ?? "result"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const visibleQuestions = useMemo(() => {
    const questions = result?.questions ?? [];
    const decisions = result?.review_decisions ?? {};
    return questions
      .map((question, index) => {
        const key = questionKey(question, index);
        return {
          question,
          index,
          images: imagesByQuestion.get(key) ?? [],
        };
      })
      .filter(({ question, index }) => {
        const key = questionKey(question, index);
        return matchesFilter(question, decisions[key], filter);
      });
  }, [result, filter, imagesByQuestion]);

  return (
    <main className="review-page">
      <nav className="top-nav">
        <Link to="/admin" className="brand-link">AI Tutor</Link>
        <div className="top-nav-links">
          <Link to="/admin" aria-current="page">管理后台</Link>
          <Link to="/student">学生端</Link>
        </div>
      </nav>

      <div className="review-layout">
        <aside className="review-sidebar">
          <section className="panel">
            <h1>解析审核台</h1>
            <form className="upload-form" onSubmit={handleUpload}>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx"
                multiple
                aria-label="选择 PDF 或 DOCX"
              />
              <div className="form-row">
                <label htmlFor="subject">科目</label>
                <input id="subject" name="subject" placeholder="math" />
              </div>
              <div className="form-row">
                <label htmlFor="grade">年级</label>
                <input id="grade" name="grade" placeholder="senior_high_1" />
              </div>
              <div className="form-row">
                <label htmlFor="year">年份</label>
                <input id="year" name="year" type="number" placeholder="2026" />
              </div>
              <button className="primary-button" type="submit" disabled={uploading}>
                {uploading ? "上传中..." : "上传并解析"}
              </button>
            </form>
            <button className="secondary-button" type="button" onClick={() => importRef.current?.click()}>
              导入结果 JSON
            </button>
            <input
              ref={importRef}
              className="visually-hidden"
              type="file"
              accept="application/json,.json"
              onChange={handleImport}
            />
          </section>

          <section className="panel doc-panel">
            <div className="panel-heading">
              <h2>文档</h2>
              <button className="icon-button" type="button" onClick={() => void fetchDocuments()}>
                刷新
              </button>
            </div>
            <div className="doc-list">
              {documents.length === 0 ? <p className="muted">暂无文档</p> : null}
              {documents.map((document) => (
                <div
                  key={document.id}
                  className={`doc-item-wrap ${selectedId === document.id ? "active" : ""}`}
                >
                  <button
                    className="doc-item"
                    type="button"
                    onClick={() => {
                      setImportedResult(null);
                      setParse(null);
                      setSelectedId(document.id);
                    }}
                  >
                    <span className="doc-name">{document.filename}</span>
                    <span className="doc-status">{document.processing_status || document.upload_status}</span>
                  </button>
                  <Link
                    className="doc-bank-link"
                    to={`/admin/questions?document=${encodeURIComponent(document.filename)}`}
                    title="查看该文档的入库题目"
                  >
                    入库
                  </Link>
                </div>
              ))}
            </div>
          </section>
        </aside>

        <section className="review-main">
          {error ? <div className="error-banner">{error}</div> : null}
          {uploadMessage ? <div className="info-banner">{uploadMessage}</div> : null}

          {selectedDocument ? (
            <header className="detail-header panel">
              <div>
                <h2>{selectedDocument.filename}</h2>
                <p>
                  {selectedDocument.subject || "未设置科目"} / {selectedDocument.grade || "未设置年级"}
                  {selectedDocument.year ? ` / ${selectedDocument.year}` : ""}
                </p>
              </div>
              <div className="task-state">
                <span>状态：{parse?.status ?? selectedDocument.processing_status}</span>
                {parse?.current_stage ? <span>阶段：{parse.current_stage}</span> : null}
                {parse?.progress !== null && parse?.progress !== undefined ? (
                  <span>进度：{Math.round(parse.progress * 100)}%</span>
                ) : null}
              </div>
            </header>
          ) : null}

          {result ? (
            <section className="result-section">
              <div className="result-toolbar">
                <div className="view-mode-switch">
                  <button
                    className={viewMode === "display" ? "active" : ""}
                    type="button"
                    onClick={() => setViewMode("display")}
                  >
                    显示效果
                  </button>
                  <button
                    className={viewMode === "review" ? "active" : ""}
                    type="button"
                    onClick={() => setViewMode("review")}
                  >
                    审核操作
                  </button>
                </div>

                <div className="filter-bar">
                  {(Object.keys(FILTER_LABELS) as ReviewFilter[]).map((item) => (
                    <button
                      key={item}
                      className={`filter-chip ${filter === item ? "active" : ""}`}
                      type="button"
                      onClick={() => setFilter(item)}
                    >
                      {FILTER_LABELS[item]}
                    </button>
                  ))}
                </div>

                <div className="result-actions">
                  <button className="secondary-button" type="button" onClick={() => setShowRaw((current) => !current)}>
                    {showRaw ? "收起原始 JSON" : "查看原始 JSON"}
                  </button>
                  <button className="secondary-button" type="button" onClick={() => void copyResult()}>
                    {copied ? "已复制" : "复制 JSON"}
                  </button>
                  <button className="secondary-button" type="button" onClick={exportResult}>
                    导出审核结果
                  </button>
                </div>
              </div>

              <div className="metric-grid">
                <div className="metric">
                  <strong>{result.questions?.length ?? 0}</strong>
                  <span>题目</span>
                </div>
                <div className="metric">
                  <strong>{summary.needsReview}</strong>
                  <span>需审核</span>
                </div>
                <div className="metric">
                  <strong>{summary.approved}</strong>
                  <span>已通过</span>
                </div>
                <div className="metric">
                  <strong>{summary.rejected}</strong>
                  <span>已驳回</span>
                </div>
                <div className="metric">
                  <strong>{summary.answerEmpty}</strong>
                  <span>答案为空</span>
                </div>
                <div className="metric">
                  <strong>{summary.discarded}</strong>
                  <span>丢弃候选</span>
                </div>
                <div className="metric">
                  <strong>{summary.composite}</strong>
                  <span>综合题</span>
                </div>
              </div>

              {showRaw ? <pre className="raw-json">{JSON.stringify(result, null, 2)}</pre> : null}

              <div className="stage-strip">
                {(result.stages ?? []).map((stage) => (
                  <span key={stage.name} title={`${stage.duration_ms ?? 0}ms`}>
                    {stage.name}
                  </span>
                ))}
              </div>

              <div className="question-list">
                {visibleQuestions.map(({ question, index, images }) => {
                  const key = questionKey(question, index);
                  return (
                    <QuestionCard
                      key={`${selectedId ?? `imported-${importedVersion}`}-${key}-${index}`}
                      question={question}
                      index={index}
                      decision={result.review_decisions?.[key]}
                      override={result.review_overrides?.[key]}
                      images={images}
                      displayOnly={viewMode === "display"}
                      canSaveToBackend={Boolean(question.question_number?.trim())}
                      saving={savingKey === key}
                      onSave={(status, comment, overrides) => saveReview(question, index, status, comment, overrides)}
                    />
                  );
                })}
              </div>
            </section>
          ) : (
            <section className="empty-state panel">
              <h2>暂无解析结果</h2>
              <p>{parse?.status === "processing" || parse?.status === "queued" ? "任务处理中" : "选择文档或导入结果 JSON"}</p>
            </section>
          )}
        </section>
      </div>
    </main>
  );
}
