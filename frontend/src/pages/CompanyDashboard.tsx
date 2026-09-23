import { Link } from "react-router-dom";
import {
  Plus,
  ArrowUpRight,
  BriefcaseBusiness,
  Layers,
  CheckCircle2,
} from "lucide-react";
import { api, useAuth, useResource } from "../lib/api";
import type { Company, Problem } from "../lib/types";
import {
  DeadlineBadge,
  Empty,
  ErrorBox,
  Loading,
  PageTitle,
  ScoreBadge,
} from "../components/ui";

export default function CompanyDashboard() {
  const { user } = useAuth();
  const r = useResource(
    () =>
      Promise.all([
        api<Problem[]>("/company/problems"),
        api<Company>("/company/me"),
      ]),
    `company-${user?.id}`,
  );
  if (!r.data) return r.error ? <ErrorBox error={r.error} /> : <Loading />;
  const [problems, company] = r.data;
  return (
    <>
      <PageTitle
        eyebrow={company.name.toUpperCase()}
        title="Пространство бизнеса"
        description="От хорошей постановки задачи — к работающему решению."
      >
        <Link className="button" to="/company/problems/new">
          <Plus size={18} />
          Создать задачу
        </Link>
      </PageTitle>
      <div className="stat-grid">
        <div className="stat">
          <BriefcaseBusiness />
          <strong>{problems.length}</strong>
          <span>Ваших задач</span>
        </div>
        <div className="stat">
          <Layers />
          <strong>
            {problems.reduce((sum, p) => sum + p.submissionCount, 0)}
          </strong>
          <span>Получено решений</span>
        </div>
        <div className="stat">
          <CheckCircle2 />
          <strong>{problems.filter((p) => p.completed).length}</strong>
          <span>Завершено проектов</span>
        </div>
      </div>
      <div className="section-heading section-space">
        <h2>Мои задачи</h2>
        <span className="muted small">
          {company.industry} · {company.city}
        </span>
      </div>
      {problems.length === 0 ? (
        <Empty
          title="Первый проект начинается с вопроса"
          text="Опишите проблему бизнеса — AI поможет превратить её в понятную задачу."
        >
          <Link className="button" to="/company/problems/new">
            Создать задачу
          </Link>
        </Empty>
      ) : (
        <div className="table-wrap panel">
          <table>
            <thead>
              <tr>
                <th>Задача</th>
                <th>Качество</th>
                <th>Дедлайн</th>
                <th>Решения</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {problems.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link className="table-title" to={`/problems/${p.id}`}>
                      {p.title}
                    </Link>
                    <span className="small muted">
                      {p.hidden
                        ? "Скрыта модератором"
                        : p.completed
                          ? "Завершена"
                          : p.winnerSubmissionId
                            ? "Ожидает вашей оценки"
                            : p.status === "DRAFT"
                              ? "Черновик"
                              : p.status === "CLOSED"
                                ? "Можно выбрать победителя"
                                : "Приём открыт"}
                    </span>
                  </td>
                  <td>
                    <ScoreBadge score={p.qualityScore} />
                  </td>
                  <td>
                    <DeadlineBadge deadline={p.deadline} />
                  </td>
                  <td>{p.submissionCount}</td>
                  <td>
                    <div className="table-actions">
                      <Link to={`/company/problems/${p.id}/submissions`}>
                        Решения <ArrowUpRight size={14} />
                      </Link>
                      {!p.winnerSubmissionId && (
                        <Link to={`/company/problems/${p.id}/edit`}>
                          {p.status === "DRAFT"
                            ? "Продолжить"
                            : "Редактировать"}
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <section className="panel company-summary">
        <h3>{company.name}</h3>
        <p>{company.description}</p>
        <span className="small muted">
          {company.email} · @{company.telegram}
        </span>
      </section>
    </>
  );
}
