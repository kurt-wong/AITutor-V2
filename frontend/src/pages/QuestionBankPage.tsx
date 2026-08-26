import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

declare global {
  interface Window {
    katex?: {
      renderToString: (tex: string, options?: Record<string, unknown>) => string;
    };
    renderMathInElement?: (element: HTMLElement, options?: Record<string, unknown>) => void;
  }
}

interface ApiEnvelope<T> {
  data: T;
}

interface CatalogSubject {
  name: string;
  question_count: number;
  grades: { name: string | null; question_count: number }[];
}

interface QuestionRow {
  id: string;
  subject_id: string;
  subject_name?: string | null;
  grade?: string | null;
  question_type_id?: string | null;
  question_type_name?: string | null;
  stem: string;
  options: { label: string; text: string }[] | null;
  answer?: string | null;
  explanation?: string | null;
  difficulty?: number | null;
  score?: number | null;
  source_type: string;
  source_document_name?: string | null;
  status: string;
  confidence?: number | null;
  occurrence_count: number;
  is_composite: boolean;
  created_at?: string | null;
  images?: {
    image_key: string;
    image_type: string;
    description?: string | null;
    image_order: number;
    page_no?: number | null;
    bbox?: unknown;
    placement?: string | null;
    source?: string | null;
    figure_id?: string | null;
  }[];
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
};

const STATUS_LABELS: Record<string, string> = {
  approved: "已入库",
  reviewing: "待审核",
  rejected: "已驳回",
  pending: "草稿",
};

const STATUS_CLASS: Record<string, string> = {
  approved: "status-approved",
  reviewing: "status-reviewing",
  rejected: "status-rejected",
  pending: "status-pending",
};

const DIFFICULTY_LABELS: Record<number, string> = {
  1: "基础",
  2: "简单",
  3: "中等",
  4: "较难",
  5: "困难",
};

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
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

function decodeName(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function QuestionImages({ images }: { images: NonNullable<QuestionRow["images"]> }) {
  if (images.length === 0) {
    return null;
  }
  // 入库题目只持久化 image_id（无 URL），实际图片渲染依赖后续
  // 后端图片服务端点；当前先展示配图标识列表。
  return (
    <div className="question-image-block">
      <strong>配图（{images.length}）</strong>
      <ul className="image-id-list">
        {images.map((image) => (
          <li key={image.image_key}>
            {image.image_key}
            {image.placement ? ` / ${image.placement}` : ""}
            {image.page_no ? ` / 第${image.page_no}页` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface TreeSelection {
  subject?: string;
  grade?: string;
}

export default function QuestionBankPage() {
  const [searchParams] = useSearchParams();
  const [catalog, setCatalog] = useState<CatalogSubject[]>([]);
  const [selection, setSelection] = useState<TreeSelection>({});
  const [questions, setQuestions] = useState<QuestionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<QuestionRow | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  // 筛选（不随目录树联动，作为附加过滤条件）
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("");
  // 文档入口：?document=<urlencoded filename>；学科入口：?subject=<学科名>
  const [documentFilter, setDocumentFilter] = useState<string>(
    () => searchParams.get("document") ?? "",
  );

  useEffect(() => {
    const doc = searchParams.get("document");
    if (doc) {
      setDocumentFilter(doc);
    }
    const subjectParam = searchParams.get("subject");
    if (subjectParam) {
      setSelection({ subject: subjectParam });
    }
  }, [searchParams]);

  useEffect(() => {
    let active = true;
    async function loadCatalog() {
      try {
        const resp = await fetch("/api/admin/catalog");
        if (!resp.ok) {
          throw new Error(`catalog 接口返回 ${resp.status}`);
        }
        const body = (await resp.json()) as ApiEnvelope<CatalogSubject[]>;
        if (active) {
          setCatalog(body.data ?? []);
        }
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : String(caught));
        }
      }
    }
    void loadCatalog();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setPage(1);
  }, [selection, statusFilter, typeFilter, difficultyFilter, documentFilter]);

  useEffect(() => {
    let active = true;
    async function loadQuestions() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          page: String(page),
          page_size: String(pageSize),
        });
        if (selection.subject) {
          params.set("subject", selection.subject);
        }
        if (selection.grade) {
          params.set("grade", selection.grade);
        }
        if (statusFilter) {
          params.set("status", statusFilter);
        }
        if (typeFilter) {
          params.set("question_type", typeFilter);
        }
        if (difficultyFilter) {
          params.set("difficulty", difficultyFilter);
        }
        if (documentFilter) {
          // 数据库 source_document_name 为 URL 编码存储，传原始编码值模糊匹配
          params.set("source_document_name", documentFilter);
        }
        const resp = await fetch(`/api/admin/questions?${params.toString()}`);
        if (!resp.ok) {
          throw new Error(`题目接口返回 ${resp.status}`);
        }
        const body = (await resp.json()) as ApiEnvelope<{
          items: QuestionRow[];
          total: number;
        }>;
        if (active) {
          setQuestions(body.data.items ?? []);
          setTotal(body.data.total ?? 0);
        }
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : String(caught));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    void loadQuestions();
    return () => {
      active = false;
    };
  }, [page, selection, statusFilter, typeFilter, difficultyFilter, documentFilter]);

  async function loadDetail(id: string) {
    setDetailLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/admin/questions/${id}`);
      if (!resp.ok) {
        throw new Error(`详情接口返回 ${resp.status}`);
      }
      const body = (await resp.json()) as ApiEnvelope<QuestionRow>;
      setDetail(body.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setDetailLoading(false);
    }
  }

  function toggleExpand(row: QuestionRow) {
    if (expandedId === row.id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(row.id);
    setDetail(null);
    void loadDetail(row.id);
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const subjectOptions = useMemo(() => {
    const options = catalog.map((s) => ({ value: s.name, label: s.name }));
    return options;
  }, [catalog]);

  const typeOptions = useMemo(() => {
    const seen = new Set<string>();
    const options: { value: string; label: string }[] = [];
    for (const q of questions) {
      const code = q.question_type_name ?? "";
      if (code && !seen.has(code)) {
        seen.add(code);
        options.push({ value: code, label: code });
      }
    }
    return options;
  }, [questions]);

  const activeDocument = documentFilter ? decodeName(documentFilter) : "";

  return (
    <main className="question-bank-page">
      <div className="question-bank-layout">
        <aside className="catalog-panel panel">
          <h2>题库目录</h2>
          {activeDocument ? (
            <div className="doc-filter-banner">
              <span>按文档筛选：</span>
              <strong title={activeDocument}>{activeDocument}</strong>
              <button
                className="text-button"
                type="button"
                onClick={() => {
                  setDocumentFilter("");
                  setSelection({});
                }}
              >
                清除
              </button>
            </div>
          ) : null}
          <div className="catalog-tree">
            <button
              className={`catalog-node catalog-root ${!selection.subject ? "active" : ""}`}
              type="button"
              onClick={() => setSelection({})}
            >
              <span>全部学科</span>
              <span className="catalog-count">
                {catalog.reduce((sum, s) => sum + s.question_count, 0)}
              </span>
            </button>
            {catalog.map((subject) => (
              <div key={subject.name} className="catalog-subject">
                <button
                  className={`catalog-node catalog-subject-node ${
                    selection.subject === subject.name && !selection.grade ? "active" : ""
                  }`}
                  type="button"
                  onClick={() => setSelection({ subject: subject.name })}
                >
                  <span>{subject.name}</span>
                  <span className="catalog-count">{subject.question_count}</span>
                </button>
                <div className="catalog-grades">
                  {subject.grades.map((grade) => (
                    <button
                      key={grade.name ?? "(未分级)"}
                      className={`catalog-node catalog-grade-node ${
                        selection.subject === subject.name && selection.grade === grade.name
                          ? "active"
                          : ""
                      }`}
                      type="button"
                      onClick={() => setSelection({ subject: subject.name, grade: grade.name ?? undefined })}
                    >
                      <span>{grade.name ?? "(未分级)"}</span>
                      <span className="catalog-count">{grade.question_count}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </aside>

        <section className="bank-main">
          <header className="bank-header panel">
            <div>
              <h2>入库题目</h2>
              <p className="muted">
                {selection.subject ? `${selection.subject}${selection.grade ? ` / ${selection.grade}` : ""}` : "全部学科"}
                {activeDocument ? ` / ${activeDocument}` : ""}
                {" — "}
                共 {total} 题
              </p>
            </div>
          </header>

          <div className="bank-filters panel">
            <select
              aria-label="学科筛选"
              value={selection.subject ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                setSelection(value ? { subject: value } : {});
              }}
            >
              <option value="">全部学科</option>
              {subjectOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              aria-label="状态筛选"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">全部状态</option>
              <option value="approved">已入库</option>
              <option value="reviewing">待审核</option>
              <option value="rejected">已驳回</option>
              <option value="pending">草稿</option>
            </select>
            <select
              aria-label="题型筛选"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              <option value="">全部题型</option>
              {typeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {TYPE_LABELS[option.value] ?? option.label}
                </option>
              ))}
            </select>
            <select
              aria-label="难度筛选"
              value={difficultyFilter}
              onChange={(event) => setDifficultyFilter(event.target.value)}
            >
              <option value="">全部难度</option>
              {[1, 2, 3, 4, 5].map((d) => (
                <option key={d} value={String(d)}>
                  {DIFFICULTY_LABELS[d]}
                </option>
              ))}
            </select>
          </div>

          {error ? <div className="error-banner">{error}</div> : null}

          <div className="bank-list">
            {loading ? <p className="muted bank-empty">加载中...</p> : null}
            {!loading && questions.length === 0 ? (
              <div className="empty-state panel">
                <h2>暂无题目</h2>
                <p>当前筛选条件下没有入库题目。</p>
              </div>
            ) : null}
            {!loading &&
              questions.map((question) => (
                <article className="question-card" key={question.id}>
                  <button
                    className="bank-row"
                    type="button"
                    onClick={() => toggleExpand(question)}
                    aria-expanded={expandedId === question.id}
                  >
                    <span className={`bank-status ${STATUS_CLASS[question.status] ?? ""}`}>
                      {STATUS_LABELS[question.status] ?? question.status}
                    </span>
                    <span className="bank-stem">
                      <MathText text={question.stem || "（题干为空）"} />
                    </span>
                    <span className="bank-meta">
                      {question.subject_name ? (
                        <span className="badge">{question.subject_name}</span>
                      ) : null}
                      {question.question_type_name ? (
                        <span className="badge">
                          {TYPE_LABELS[question.question_type_name] ?? question.question_type_name}
                        </span>
                      ) : null}
                      {question.difficulty ? (
                        <span className="badge">{DIFFICULTY_LABELS[question.difficulty]}</span>
                      ) : null}
                      <span className="badge">
                        {question.confidence !== null && question.confidence !== undefined
                          ? `置信 ${Number(question.confidence).toFixed(2)}`
                          : "置信 -"}
                      </span>
                      {question.occurrence_count > 1 ? (
                        <span className="badge">出现 {question.occurrence_count} 次</span>
                      ) : null}
                      {question.is_composite ? <span className="badge">综合题</span> : null}
                    </span>
                  </button>

                  {expandedId === question.id ? (
                    <div className="bank-detail">
                      {detailLoading ? (
                        <p className="muted">加载详情...</p>
                      ) : detail ? (
                        <>
                          <div className="detail-meta">
                            {detail.grade ? <span>年级：{detail.grade}</span> : null}
                            {detail.source_document_name ? (
                              <span>来源：{decodeName(detail.source_document_name)}</span>
                            ) : null}
                            {detail.score ? <span>分值：{detail.score}</span> : null}
                            {detail.created_at ? (
                              <span>入库：{new Date(detail.created_at).toLocaleString()}</span>
                            ) : null}
                          </div>
                          <div className="question-content">
                            <MathText className="stem-text" text={detail.stem || "（题干为空）"} />
                            {detail.options && detail.options.length > 0 ? (
                              <ol className="option-list">
                                {detail.options.map((option) => (
                                  <li key={option.label}>
                                    <strong>{option.label}.</strong> <MathText text={option.text} />
                                  </li>
                                ))}
                              </ol>
                            ) : (
                              <p className="muted">无选项</p>
                            )}
                            <QuestionImages images={detail.images ?? []} />
                            <dl className="answer-grid">
                              <div>
                                <dt>答案</dt>
                                <dd>
                                  <MathText text={detail.answer || "未匹配"} />
                                </dd>
                              </div>
                              {detail.explanation ? (
                                <div>
                                  <dt>详解</dt>
                                  <dd>
                                    <MathText text={detail.explanation} />
                                  </dd>
                                </div>
                              ) : null}
                            </dl>
                          </div>
                        </>
                      ) : (
                        <p className="muted">详情加载失败</p>
                      )}
                    </div>
                  ) : null}
                </article>
              ))}
          </div>

          {totalPages > 1 ? (
            <div className="bank-pagination">
              <button
                className="secondary-button"
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </button>
              <span className="muted">
                {page} / {totalPages}
              </span>
              <button
                className="secondary-button"
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                下一页
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
