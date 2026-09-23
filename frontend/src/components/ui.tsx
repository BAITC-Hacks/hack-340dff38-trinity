import { useEffect, useRef } from "react";
import type { ReactNode, FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Clock3,
  Sparkles,
  ShieldCheck,
  X,
  AlertCircle,
  Check,
  Send,
  MessageSquare,
  LockKeyhole,
} from "lucide-react";
import { api, useAction, useAuth, useResource } from "../lib/api";
import type {
  Analysis,
  SolutionAnalysis,
  Problem,
  Submission,
  Message,
  Role,
} from "../lib/types";

export const labels: Record<string, string> = {
  context: "Контекст и потребность",
  data: "Данные и материалы",
  result: "Ожидаемый результат",
  success: "Критерии успеха",
  constraints: "Ограничения",
  users: "Пользователи",
  communication: "Связь с бизнесом",
  creativity: "Креативность",
  effectiveness: "Эффективность",
  implementation: "Качество реализации",
  feasibility: "Реалистичность",
  available_data: "Данные",
  success_criteria: "Критерии успеха",
  expected_result: "Результат",
  deadline: "Дедлайн",
  need: "Потребность",
  title: "Название",
  industry: "Отрасль",
  interaction_format: "Формат общения",
  business_contact: "Контакт",
};
export const date = (value: string, time = false) =>
  new Date(value).toLocaleString(
    "ru-RU",
    time
      ? { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }
      : { day: "numeric", month: "short", year: "numeric" },
  );
export const scoreLevel = (score: number) =>
  score >= 90
    ? "Приоритетная"
    : score >= 70
      ? "Готова к работе"
      : score >= 40
        ? "Рабочая"
        : "Нужны уточнения";
export function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div className="notice error" role="alert">
      <AlertCircle size={18} />
      <span>{error}</span>
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <span className="spinner" />
      Загружаем пространство…
    </div>
  );
}
export function Empty({
  title,
  text,
  children,
}: {
  title: string;
  text?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Sparkles size={28} />
      <h3>{title}</h3>
      {text && <p>{text}</p>}
      {children}
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {children}
    </div>
  );
}
export function ScoreBadge({
  score,
  large = false,
}: {
  score: number;
  large?: boolean;
}) {
  return (
    <div
      className={`score-badge ${large ? "large" : ""} ${score < 40 ? "low" : ""}`}
      title="Качество постановки задачи"
    >
      <Sparkles size={large ? 20 : 15} />
      <strong>{score}</strong>
      <span>/ 100</span>
    </div>
  );
}
export function DeadlineBadge({ deadline }: { deadline: string }) {
  const left = new Date(deadline).getTime() - Date.now();
  return (
    <span className={`deadline ${left > 0 && left < 86400000 ? "soon" : ""}`}>
      <Clock3 size={14} />
      {left <= 0
        ? "Приём завершён"
        : left < 86400000
          ? `Осталось ${Math.max(1, Math.ceil(left / 3600000))} ч`
          : `До ${date(deadline)}`}
    </span>
  );
}
export function ProblemCard({ problem: p }: { problem: Problem }) {
  return (
    <Link className="problem-card" to={`/problems/${p.id}`}>
      <div className="card-top">
        <span className={`industry ${p.industry.toLowerCase()}`}>
          {p.industry}
        </span>
        <span className="card-arrow">
          <ArrowUpRight size={19} />
        </span>
      </div>
      <h3>{p.title}</h3>
      <p className="card-company">
        <span className="company-mark">{p.company.name.slice(0, 1)}</span>
        {p.company.name}
        <span>· {p.company.city}</span>
      </p>
      <p className="card-context">{p.context}</p>
      <div className="quality-line">
        <ScoreBadge score={p.qualityScore} />
        <span className="readiness">{scoreLevel(p.qualityScore)}</span>
      </div>
      <div className="card-bottom">
        <DeadlineBadge deadline={p.deadline} />
        <span>{p.submissionCount} решений</span>
      </div>
      {p.completed && (
        <div className="completed-strip">
          <Check size={14} />
          Победитель выбран
        </div>
      )}
    </Link>
  );
}
export function ScoreBreakdown({ analysis }: { analysis: Analysis }) {
  return (
    <div className="score-breakdown">
      <div className="section-heading">
        <h3>Качество задачи</h3>
        <ScoreBadge score={analysis.overallScore} />
      </div>
      <p className="small muted">
        {scoreLevel(analysis.overallScore)} ·{" "}
        {analysis.source === "claude" ? "Claude" : "Демо-анализ"}
      </p>
      {Object.entries(analysis.criteria).map(([key, c]) => (
        <details key={key} className="criterion">
          <summary>
            <span>{labels[key] || key}</span>
            <strong>
              {c.score}
              <span> / {c.maxScore}</span>
            </strong>
          </summary>
          <div className="criterion-details">
            <p>{c.reasoning}</p>
            {c.missing.length > 0 && (
              <p>
                <strong>Не хватает:</strong> {c.missing.join(" ")}
              </p>
            )}
            {c.recommendations.map((r, i) => (
              <p key={i}>{r}</p>
            ))}
          </div>
          <div className="progress">
            <span style={{ width: `${(c.score / c.maxScore) * 100}%` }} />
          </div>
        </details>
      ))}
    </div>
  );
}
export function AIAnalysisPanel({
  analysis: a,
}: {
  analysis: SolutionAnalysis;
}) {
  return (
    <section className="ai-panel">
      <div className="ai-panel-header">
        <div>
          <div className="eyebrow">
            <Sparkles size={15} />
            AI SOLUTION ANALYSIS
          </div>
          <h2>Взгляд на решение</h2>
          <p>{a.summary}</p>
          <span className="ai-mode">
            {a.source === "claude"
              ? "Анализ Claude"
              : a.source === "mock_fallback"
                ? "Резервный демо-анализ"
                : "Детерминированный демо-анализ"}
          </span>
        </div>
        <div
          className="score-ring"
          style={
            { "--score": `${a.overallScore * 3.6}deg` } as React.CSSProperties
          }
        >
          <div>
            <strong>{a.overallScore}</strong>
            <span>из 100</span>
          </div>
        </div>
      </div>
      <div className="ai-criteria">
        {Object.entries(a.criteria).map(([key, c]) => (
          <details key={key}>
            <summary>
              <span>{labels[key] || key}</span>
              <strong>
                {c.score}
                <small> / 25</small>
              </strong>
              <div className="progress">
                <span style={{ width: `${c.score * 4}%` }} />
              </div>
            </summary>
            <p>{c.reasoning}</p>
            {[
              ["Сильные стороны", c.strengths],
              ["Риски", c.weaknesses],
              ["Рекомендации", c.recommendations],
            ].map(([title, list]) => (
              <div key={title as string}>
                <b>{title}</b>
                <ul>
                  {(list as string[]).map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            ))}
          </details>
        ))}
      </div>
      <div className="ai-insights">
        {[
          ["Сильные стороны", a.keyStrengths],
          ["Что проверить", a.keyRisks],
          ["Как улучшить", a.recommendedImprovements],
        ].map(([title, list]) => (
          <div key={title as string}>
            <h4>{title}</h4>
            <ul>
              {(list as string[]).map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="ai-advisory">
        <ShieldCheck size={18} />
        <span>
          AI analysis is advisory. The final decision is made by the business.
        </span>
      </div>
    </section>
  );
}
export function SubmissionCard({
  submission: s,
  children,
}: {
  submission: Submission;
  children?: ReactNode;
}) {
  return (
    <article className="panel submission-card">
      <div className="section-heading">
        <span className="pill">
          {s.status === "WINNER"
            ? "Победитель"
            : s.status === "NOT_SELECTED"
              ? "Не выбрано"
              : "Отправлено"}
        </span>
        {s.aiAnalysis && (
          <span className="small">
            AI · <strong>{s.aiAnalysis.overallScore}/100</strong>
          </span>
        )}
      </div>
      <h3>{s.title}</h3>
      <p className="muted">{s.problemTitle || s.summary}</p>
      {s.teamName && (
        <p className="small">
          {s.teamName} · {s.members?.length} участников
        </p>
      )}
      {children}
    </article>
  );
}
export function AnonymousSolutionCard({
  submission: s,
  active,
  onClick,
}: {
  submission: Submission;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`solution-selector ${active ? "selected" : ""}`}
      onClick={onClick}
    >
      <div>
        <span className="solution-avatar">
          {s.anonymous ? (
            <LockKeyhole size={19} />
          ) : (
            s.anonymousNumber.toString().padStart(2, "0")
          )}
        </span>
        <strong>{s.anonymous ? s.label : s.teamName}</strong>
      </div>
      <p>{s.title}</p>
      <span>
        {s.status === "WINNER"
          ? "Победитель"
          : `AI-анализ: ${s.aiAnalysis?.overallScore ?? "—"} / 100`}
      </span>
    </button>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog ref={ref} onCancel={onClose} className="modal">
      <div className="section-heading">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Закрыть" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function TextComposer({
  placeholder,
  button = "Отправить",
  onSend,
}: {
  placeholder: string;
  button?: string;
  onSend: (text: string) => Promise<unknown>;
}) {
  const action = useAction();
  const ref = useRef<HTMLTextAreaElement>(null);
  function submit(event: FormEvent) {
    event.preventDefault();
    const text = ref.current?.value.trim();
    if (text)
      void action.run(async () => {
        await onSend(text);
        if (ref.current) ref.current.value = "";
      });
  }
  return (
    <form onSubmit={submit} className="composer">
      <textarea
        ref={ref}
        aria-label={placeholder}
        placeholder={placeholder}
        required
        maxLength={3000}
        rows={2}
      />
      <ErrorBox error={action.error} />
      <button className="button small-button" disabled={action.busy}>
        <Send size={15} />
        {action.busy ? "Отправляем…" : button}
      </button>
    </form>
  );
}
export function QuestionSection({
  problem,
  reload,
}: {
  problem: Problem;
  reload: () => void;
}) {
  const { user } = useAuth();
  const owner = user?.companyId === problem.company.id;
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Вопросы и ответы</h2>
        <span className="count">{problem.questions.length}</span>
      </div>
      {problem.questions.map((q) => (
        <div className="public-message" key={q.id}>
          <div className="small muted">
            {q.author} · {date(q.createdAt)}
          </div>
          <p>{q.text}</p>
          {q.answers.map((a) => (
            <div className="answer" key={a.id}>
              <strong className="small">
                {a.author} · представитель бизнеса
              </strong>
              <p>{a.text}</p>
            </div>
          ))}
          {owner && (
            <TextComposer
              placeholder="Ответить от имени компании"
              onSend={async (text) => {
                await api(`/questions/${q.id}/answers`, "POST", { text });
                reload();
              }}
            />
          )}
        </div>
      ))}
      {!problem.questions.length && (
        <p className="muted">
          Задайте первый вопрос о данных, ограничениях или результате.
        </p>
      )}
      {user && user.role !== "ADMIN" ? (
        <TextComposer
          placeholder="Что вы хотите уточнить у бизнеса?"
          button="Задать вопрос"
          onSend={async (text) => {
            await api(`/problems/${problem.id}/questions`, "POST", { text });
            reload();
          }}
        />
      ) : (
        <Link className="text-link" to="/login">
          Войти, чтобы задать вопрос <ArrowRight size={15} />
        </Link>
      )}
    </section>
  );
}
export function CommentsSection({
  problem,
  reload,
}: {
  problem: Problem;
  reload: () => void;
}) {
  const { user } = useAuth();
  return (
    <section className="panel">
      <h2>Обсуждение и улучшения</h2>
      {problem.comments.map((c) => (
        <div className="public-message" key={c.id}>
          <span className="small muted">
            {c.author} · {date(c.createdAt)}
          </span>
          <p>{c.text}</p>
        </div>
      ))}
      {user && user.role !== "ADMIN" ? (
        <TextComposer
          placeholder="Предложите улучшение или альтернативный подход"
          onSend={async (text) => {
            await api(`/problems/${problem.id}/comments`, "POST", { text });
            reload();
          }}
        />
      ) : (
        <p className="muted">
          Войдите как студент или компания, чтобы участвовать в обсуждении.
        </p>
      )}
    </section>
  );
}
export function ChatPanel({ submissionId }: { submissionId: string }) {
  const resource = useResource(
    () => api<Message[]>(`/submissions/${submissionId}/messages`),
    submissionId,
  );
  useEffect(() => {
    const timer = window.setInterval(resource.reload, 6000);
    return () => clearInterval(timer);
  }, [submissionId]);
  return (
    <section className="panel chat">
      <div className="section-heading">
        <h3>
          <MessageSquare size={18} /> Обсуждение решения
        </h3>
        <span className="small muted">Личный диалог</span>
      </div>
      <p className="small muted">
        До выбора победителя не указывайте имена, контакты и другие сведения об
        авторах.
      </p>
      <ErrorBox error={resource.error} />
      <div className="messages">
        {resource.data?.map((m) => (
          <div className={`message ${m.isMine ? "mine" : ""}`} key={m.id}>
            <b>{m.sender}</b>
            <p>{m.text}</p>
            <time>{date(m.createdAt, true)}</time>
          </div>
        ))}
        {resource.data?.length === 0 && (
          <p className="muted">Сообщений пока нет.</p>
        )}
      </div>
      <TextComposer
        placeholder="Написать сообщение"
        onSend={async (text) => {
          await api(`/submissions/${submissionId}/messages`, "POST", { text });
          resource.reload();
        }}
      />
    </section>
  );
}
export function AccessGate({
  role,
  children,
}: {
  role: Role;
  children: ReactNode;
}) {
  const { user, ready } = useAuth();
  if (!ready) return <Loading />;
  if (user?.role !== role)
    return (
      <Empty
        title="Выберите подходящий демо-аккаунт"
        text={`Этот раздел доступен роли ${role === "STUDENT" ? "«Студент»" : role === "COMPANY" ? "«Компания»" : "«Администратор»"}.`}
      >
        <Link to="/login" className="button">
          Сменить роль <ArrowRight size={16} />
        </Link>
      </Empty>
    );
  return <>{children}</>;
}
