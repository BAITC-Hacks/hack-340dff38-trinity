import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpRight,
  Mail,
  Send,
  FileText,
  CheckCircle2,
  Trophy,
  Users,
} from "lucide-react";
import { api, useAuth, useResource } from "../lib/api";
import type { Problem } from "../lib/types";
import {
  AIAnalysisPanel,
  CommentsSection,
  DeadlineBadge,
  ErrorBox,
  Loading,
  PageTitle,
  QuestionSection,
  ScoreBreakdown,
  date,
  labels,
} from "../components/ui";

export default function ProblemDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const resource = useResource(
    () => api<Problem>(`/problems/${id}`),
    `problem-${id}-${user?.id}`,
  );
  if (!resource.data)
    return resource.error ? <ErrorBox error={resource.error} /> : <Loading />;
  const p = resource.data;
  const owner = user?.companyId === p.company.id;
  const sections: [string, string][] = [
    ["Контекст", p.context],
    ["Что нужно изменить", p.need],
    ["Пользователи", p.users],
    ["Доступные данные", p.availableData],
    ["Ограничения", p.constraints],
    ["Ожидаемый результат", p.expectedResult],
    ["Критерии успеха", p.successCriteria],
  ];
  return (
    <>
      <Link className="back-link" to="/">
        <ArrowLeft size={16} />
        Все задачи
      </Link>
      <PageTitle
        eyebrow={`${p.company.name} / ${p.industry}`}
        title={p.title}
      />
      <div className="detail-meta">
        <span className="pill">
          {p.completed
            ? "Завершена"
            : p.status === "CLOSED"
              ? "Оценка решений"
              : p.status === "DRAFT"
                ? "Черновик"
                : "Открыта для решений"}
        </span>
        <DeadlineBadge deadline={p.deadline} />
        <span>
          <Users size={16} />
          {p.submissionCount} решений
        </span>
      </div>
      {p.revisions.length > 0 && (
        <div className="notice">
          <FileText size={18} />
          <span>
            Задача обновлена {date(p.revisions[0].createdAt, true)}. Изменены:{" "}
            {p.revisions[0].changedFields.map((f) => labels[f] || f).join(", ")}
            .
          </span>
        </div>
      )}
      <ErrorBox error={resource.error} />
      <div className="detail-layout">
        <div className="stack">
          <section className="panel problem-description">
            {sections.map(([title, value]) => (
              <div className="description-section" key={title}>
                <h2>{title}</h2>
                <p>{value || "Компания пока не уточнила этот раздел."}</p>
              </div>
            ))}
          </section>
          {p.winner && (
            <section className="panel winner-public">
              <div className="eyebrow">
                <Trophy size={17} />
                ПОБЕДИВШЕЕ РЕШЕНИЕ
              </div>
              <h2>{p.winner.title}</h2>
              <p className="muted">
                {p.winner.teamName} · оценка компании{" "}
                <strong>{p.companyScore} / 100</strong>
              </p>
              <p>{p.winner.solutionDescription}</p>
              <h3>Реализация</h3>
              <p>{p.winner.implementationDetails}</p>
              <div className="button-row">
                {p.winner.demoUrl && (
                  <a
                    className="button secondary"
                    href={p.winner.demoUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Демо <ArrowUpRight size={16} />
                  </a>
                )}
                {p.winner.repositoryUrl && (
                  <a
                    className="button secondary"
                    href={p.winner.repositoryUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Репозиторий <ArrowUpRight size={16} />
                  </a>
                )}
              </div>
              <p>{p.feedback}</p>
              {p.winner.aiAnalysis && (
                <AIAnalysisPanel analysis={p.winner.aiAnalysis} />
              )}
            </section>
          )}
          <QuestionSection problem={p} reload={resource.reload} />
          {p.completed && (
            <CommentsSection problem={p} reload={resource.reload} />
          )}
        </div>
        <aside className="stack">
          <section className="panel action-panel">
            <div className="eyebrow">СЛЕДУЮЩИЙ ШАГ</div>
            <h3>
              {owner
                ? "Ваша задача"
                : p.acceptingSubmissions
                  ? "Есть решение?"
                  : "Приём работ завершён"}
            </h3>
            <p className="muted">
              {owner
                ? "Следите за решениями и обсуждайте детали с командами."
                : "Отправьте готовый проект от команды или участвуйте соло."}
            </p>
            {owner ? (
              <>
                <Link
                  className="button full"
                  to={`/company/problems/${p.id}/submissions`}
                >
                  Смотреть решения <ArrowUpRight size={16} />
                </Link>
                {!p.winnerSubmissionId && (
                  <Link
                    className="button secondary full"
                    to={`/company/problems/${p.id}/edit`}
                  >
                    Редактировать задачу
                  </Link>
                )}
              </>
            ) : (
              p.acceptingSubmissions && (
                <Link
                  className="button full"
                  to={
                    user?.role === "STUDENT"
                      ? `/student/problems/${p.id}/submit`
                      : "/login"
                  }
                >
                  Отправить решение <ArrowUpRight size={16} />
                </Link>
              )
            )}
            <p className="small muted">
              Дедлайн: {date(p.deadline, true)}
              <br />
              Время указано в часовом поясе вашего устройства.
            </p>
          </section>
          <section className="panel">
            <ScoreBreakdown analysis={p.qualityAnalysis} />
          </section>
          <section className="panel contact-panel">
            <div className="company-profile">
              <span className="company-logo">{p.company.name[0]}</span>
              <div>
                <h3>{p.company.name}</h3>
                <span className="muted small">
                  {p.company.city} · {p.industry}
                </span>
              </div>
            </div>
            <p>{p.company.description}</p>
            <h4>Связаться с бизнесом</h4>
            <a href={`mailto:${p.company.email}`}>
              <Mail size={17} />
              {p.company.email}
            </a>
            {p.company.telegram && (
              <a
                href={`https://t.me/${p.company.telegram.replace("@", "")}`}
                target="_blank"
                rel="noreferrer"
              >
                <Send size={17} />@{p.company.telegram}
              </a>
            )}
            <p className="small muted">{p.businessContact}</p>
            <p className="small muted">{p.interactionFormat}</p>
            <div className="small privacy-note">
              <CheckCircle2 size={15} /> Контакты доступны всем участникам
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
