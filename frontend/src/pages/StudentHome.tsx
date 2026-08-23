import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

interface ApiEnvelope<T> {
  data: T;
}

interface QuestionItem {
  id: string;
  subject_id: string;
  grade: string | null;
  stem: string;
  options: { label: string; text: string }[] | null;
  answer: string | null;
  explanation: string | null;
  difficulty: number | null;
  score: number | null;
  source_type: string;
  source_document_name: string | null;
  status: string;
  confidence: number | null;
  occurrence_count: number;
  is_composite: boolean;
  created_at: string | null;
  images: {
    image_key: string;
    image_type: string;
    url: string | null;
    placement: string | null;
  }[];
}

interface StatisticsData {
  total_questions: number;
  question_type_distribution: Record<string, number>;
  knowledge_point_distribution: Record<string, number>;
  difficulty_distribution: Record<string, number>;
  year_trend: { year: number; count: number }[];
  kp_year_trend: { knowledge_point: string; year: number; count: number }[];
}

const DIFFICULTY_LABELS: Record<number, string> = {
  1: "基础",
  2: "简单",
  3: "中等",
  4: "较难",
  5: "困难",
};

const DIFFICULTY_COLORS: Record<number, string> = {
  1: "#16803c",
  2: "#2e7d32",
  3: "#b45309",
  4: "#e65100",
  5: "#b42318",
};

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMathText(value: string): string {
  const katex = (window as unknown as Record<string, unknown>).katex as
    | { renderToString: (tex: string, options?: Record<string, unknown>) => string }
    | undefined;
  if (!katex) return escapeHtml(value);

  const parts = value.split(/(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g);
  return parts
    .map((part) => {
      if (part.startsWith("$$") && part.endsWith("$$") && part.length > 4) {
        try {
          return katex.renderToString(part.slice(2, -2), { displayMode: true, throwOnError: false });
        } catch {
          return escapeHtml(part);
        }
      }
      if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
        try {
          return katex.renderToString(part.slice(1, -1), { displayMode: false, throwOnError: false });
        } catch {
          return escapeHtml(part);
        }
      }
      return escapeHtml(part);
    })
    .join("");
}

function MathText({ text, className = "" }: { text: string; className?: string }) {
  return (
    <span
      className={`math-content ${className}`}
      dangerouslySetInnerHTML={{ __html: renderMathText(text) }}
    />
  );
}

export default function StudentHome() {
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [stats, setStats] = useState<StatisticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subjectFilter, setSubjectFilter] = useState<string>("all");
  const [difficultyFilter, setDifficultyFilter] = useState<number | null>(null);
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  useEffect(() => {
    void loadData();
  }, [page]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const offset = (page - 1) * pageSize;
      const params = new URLSearchParams({
        status: "approved",
        page: String(page),
        page_size: String(pageSize),
      });
      if (subjectFilter !== "all") params.set("subject", subjectFilter);
      if (difficultyFilter !== null) params.set("difficulty", String(difficultyFilter));

      const [qResp, sResp] = await Promise.all([
        fetch(`/api/admin/questions?${params}`),
        fetch("/api/admin/statistics"),
      ]);

      if (!qResp.ok) throw new Error(`题目接口 ${qResp.status}`);
      if (!sResp.ok) throw new Error(`统计接口 ${sResp.status}`);

      const qData = (await qResp.json()) as ApiEnvelope<{ items: QuestionItem[]; total: number }>;
      const sData = (await sResp.json()) as ApiEnvelope<StatisticsData>;

      setQuestions(qData.data.items);
      setTotal(qData.data.total);
      setStats(sData.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  }

  function toggleReveal(id: string) {
    setRevealedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function applyFilter(subject: string) {
    setSubjectFilter(subject);
    setPage(1);
    // reload will happen via useEffect if page was already 1
    // so trigger manually
    setTimeout(() => void loadData(), 0);
  }

  function applyDifficultyFilter(d: number | null) {
    setDifficultyFilter(d);
    setPage(1);
    setTimeout(() => void loadData(), 0);
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Extract unique subjects from stats
  const subjects = useMemo(() => {
    if (!stats) return [];
    return Object.keys(stats.question_type_distribution).sort();
  }, [stats]);

  return (
    <main className="student-page">
      <nav className="top-nav" aria-label="主导航">
        <Link to="/student" className="brand-link">AI Tutor</Link>
        <div className="top-nav-links">
          <Link to="/student" aria-current="page">学生端</Link>
          <Link to="/admin">管理后台</Link>
        </div>
      </nav>

      <section className="student-dashboard">
        <header className="student-intro">
          <span className="eyebrow">AI Tutor</span>
          <h1>题库练习</h1>
        </header>

        {/* 统计概览 */}
        <div className="student-metrics">
          <div className="student-metric">
            <strong>{stats?.total_questions ?? "--"}</strong>
            <span>题库总量</span>
          </div>
          <div className="student-metric">
            <strong>{Object.keys(stats?.question_type_distribution ?? {}).length}</strong>
            <span>题型</span>
          </div>
          <div className="student-metric">
            <strong>{Object.keys(stats?.knowledge_point_distribution ?? {}).length}</strong>
            <span>知识点</span>
          </div>
          <div className="student-metric">
            <strong>{total}</strong>
            <span>当前筛选</span>
          </div>
        </div>

        {/* 筛选栏 */}
        <div className="filter-bar" style={{ marginBottom: 16 }}>
          <button
            className={`filter-chip ${subjectFilter === "all" ? "active" : ""}`}
            type="button"
            onClick={() => applyFilter("all")}
          >
            全部
          </button>
          {["数学", "物理", "化学", "英语", "语文", "生物", "政治", "历史", "地理"].map((s) => (
            <button
              key={s}
              className={`filter-chip ${subjectFilter === s ? "active" : ""}`}
              type="button"
              onClick={() => applyFilter(s)}
            >
              {s}
            </button>
          ))}
        </div>

        {/* 难度筛选 */}
        <div className="filter-bar" style={{ marginBottom: 20 }}>
          <span style={{ fontSize: 13, color: "var(--ink-muted-48)", marginRight: 8 }}>难度：</span>
          <button
            className={`filter-chip ${difficultyFilter === null ? "active" : ""}`}
            type="button"
            onClick={() => applyDifficultyFilter(null)}
          >
            全部
          </button>
          {[1, 2, 3, 4, 5].map((d) => (
            <button
              key={d}
              className={`filter-chip ${difficultyFilter === d ? "active" : ""}`}
              type="button"
              onClick={() => applyDifficultyFilter(d)}
            >
              {DIFFICULTY_LABELS[d]}
            </button>
          ))}
        </div>

        {/* 错误提示 */}
        {error ? <div className="error-banner">{error}</div> : null}

        {/* 加载中 */}
        {loading ? <p className="muted" style={{ padding: 20 }}>加载中...</p> : null}

        {/* 题目列表 */}
        {!loading && questions.length === 0 ? (
          <div className="empty-state panel">
            <h2>暂无题目</h2>
            <p>题库中还没有已审核的题目。请先在管理后台上传试卷并完成审核。</p>
          </div>
        ) : null}

        <div className="question-list">
          {questions.map((q, index) => {
            const revealed = revealedIds.has(q.id);
            const diffLabel = q.difficulty ? DIFFICULTY_LABELS[q.difficulty] : null;
            const diffColor = q.difficulty ? DIFFICULTY_COLORS[q.difficulty] : null;

            return (
              <article key={q.id} className="question-card">
                <div className="question-card-header">
                  <div className="question-title">
                    <strong>第 {index + 1 + (page - 1) * pageSize} 题</strong>
                    {q.is_composite ? <span>综合题</span> : null}
                    {diffLabel ? (
                      <span style={{ color: diffColor ?? undefined, fontWeight: 500, fontSize: 13 }}>
                        {diffLabel}
                      </span>
                    ) : null}
                    {q.occurrence_count > 1 ? (
                      <span style={{ fontSize: 12, color: "var(--ink-muted-48)" }}>
                        出现 {q.occurrence_count} 次
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="question-content">
                  {/* 题干 */}
                  {q.stem ? (
                    <MathText className="stem-text" text={q.stem} />
                  ) : (
                    <p className="muted">（题干为空）</p>
                  )}

                  {/* 选项 */}
                  {q.options && q.options.length > 0 ? (
                    <ol className="option-list">
                      {q.options.map((opt) => (
                        <li key={opt.label}>
                          <strong>{opt.label}.</strong> <MathText text={opt.text} />
                        </li>
                      ))}
                    </ol>
                  ) : null}

                  {/* 答案/详解（点击展开） */}
                  <div style={{ marginTop: 12 }}>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => toggleReveal(q.id)}
                      style={{ fontSize: 14 }}
                    >
                      {revealed ? "收起答案" : "查看答案"}
                    </button>
                  </div>

                  {revealed ? (
                    <div style={{ marginTop: 12, padding: "12px 16px", background: "var(--surface-pearl)", borderRadius: "var(--radius-sm)" }}>
                      {q.answer ? (
                        <div style={{ marginBottom: 8 }}>
                          <strong style={{ color: "var(--green)" }}>答案：</strong>
                          <MathText text={q.answer} />
                        </div>
                      ) : (
                        <div style={{ marginBottom: 8, color: "var(--ink-muted-48)" }}>
                          答案未匹配
                        </div>
                      )}
                      {q.explanation ? (
                        <div>
                          <strong style={{ color: "var(--primary)" }}>详解：</strong>
                          <MathText text={q.explanation} />
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>

        {/* 分页 */}
        {totalPages > 1 ? (
          <div style={{ display: "flex", justifyContent: "center", gap: 8, padding: "20px 0" }}>
            <button
              className="secondary-button"
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              上一页
            </button>
            <span style={{ lineHeight: "36px", fontSize: 14, color: "var(--ink-muted-48)" }}>
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
    </main>
  );
}
