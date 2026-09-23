import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ShieldCheck,
  Trophy,
  Clock3,
  ArrowUpRight,
  CheckCircle2,
  Users,
} from "lucide-react";
import { api, useAction, useResource } from "../lib/api";
import type { Problem, Submission } from "../lib/types";
import {
  AIAnalysisPanel,
  AnonymousSolutionCard,
  ChatPanel,
  DeadlineBadge,
  Empty,
  ErrorBox,
  Loading,
  Modal,
  PageTitle,
} from "../components/ui";

export default function Review() {
  const { id } = useParams();
  const action = useAction();
  const r = useResource(
    () =>
      Promise.all([
        api<{ problem: Problem; items: Submission[] }>(
          `/company/problems/${id}/submissions`,
        ),
        api<{ demoTools: boolean }>("/health"),
      ]),
    `review-${id}`,
  );
  const [selected, setSelected] = useState("");
  const [confirm, setConfirm] = useState<"winner" | "expire" | null>(null);
  const [score, setScore] = useState(90);
  const [feedback, setFeedback] = useState("");
  if (!r.data) return r.error ? <ErrorBox error={r.error} /> : <Loading />;
  const [{ problem: p, items }, health] = r.data;
  const s = items.find((x) => x.id === selected) || items[0];
  const expired = Date.now() >= new Date(p.deadline).getTime();
  const winner = items.find((x) => x.id === p.winnerSubmissionId);
  async function confirmAction() {
    await api(
      confirm === "winner"
        ? `/problems/${id}/select-winner`
        : `/demo/problems/${id}/expire`,
      "POST",
      confirm === "winner" ? { submissionId: s.id } : undefined,
    );
    setConfirm(null);
    r.reload();
  }
  return (
    <>
      <Link className="back-link" to="/company/dashboard">
        <ArrowLeft size={16} />
        Кабинет компании
      </Link>
      <PageTitle
        eyebrow="ПРОСТРАНСТВО РЕШЕНИЙ"
        title="Сначала решение. Потом — знакомство."
        description={p.title}
      >
        <DeadlineBadge deadline={p.deadline} />
      </PageTitle>
      <ErrorBox error={r.error} />
      <ErrorBox error={action.error} />
      {!p.winnerSubmissionId ? (
        <div className="review-notice">
          <ShieldCheck size={24} />
          <div>
            <strong>Анонимное рассмотрение</strong>
            <p>
              Вы оцениваете подход и реализацию. Авторы всех работ раскроются
              после вашего окончательного выбора.
            </p>
          </div>
          {!expired && health.demoTools && p.status !== "DRAFT" && (
            <button
              className="button secondary"
              onClick={() => {
                action.clear();
                setConfirm("expire");
              }}
            >
              <Clock3 size={16} />
              Завершить приём (демо)
            </button>
          )}
        </div>
      ) : (
        <div className="notice success">
          <Trophy size={22} />
          <span>
            Победитель:{" "}
            <strong>{winner?.teamName || "выбранная команда"}</strong>. Выбор
            зафиксирован; данные команд раскрыты.
          </span>
        </div>
      )}
      {p.winnerSubmissionId && p.companyScore === null && (
        <form
          className="panel winner-score-form"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => {
              await api(`/problems/${id}/winner-score`, "POST", {
                score,
                feedback,
              });
              r.reload();
            });
          }}
        >
          <div>
            <div className="eyebrow">ФИНАЛЬНЫЙ ШАГ</div>
            <h2>Оцените победившее решение</h2>
            <p className="muted">
              Баллы получит только команда-победитель, поровну между
              участниками.
            </p>
          </div>
          <div className="form-columns">
            <label>
              Оценка компании, 0–100
              <input
                required
                type="number"
                min={0}
                max={100}
                step={1}
                value={score}
                onChange={(e) => setScore(Number(e.target.value))}
              />
            </label>
            <label>
              Комментарий
              <input
                maxLength={3000}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Что особенно удалось?"
              />
            </label>
          </div>
          <p className="small muted">
            Каждому участнику:{" "}
            {(score / (winner?.members?.length || 1)).toFixed(2)} балла. После
            сохранения оценку изменить нельзя.
          </p>
          <button className="button" disabled={action.busy}>
            <CheckCircle2 size={17} />
            {action.busy ? "Начисляем…" : "Сохранить оценку и начислить баллы"}
          </button>
        </form>
      )}
      {p.companyScore !== null && (
        <div className="score-result">
          <strong>
            {p.companyScore}
            <span>/100</span>
          </strong>
          <div>
            <h3>Оценка компании сохранена</h3>
            <p>
              Баллы начислены участникам победившей команды. Решение
              опубликовано на странице задачи.
            </p>
            <Link className="text-link" to={`/problems/${p.id}`}>
              Открыть результат <ArrowUpRight size={15} />
            </Link>
          </div>
        </div>
      )}
      {items.length ? (
        <div className="review-layout">
          <aside className="solution-list">
            <div className="section-heading">
              <h3>Решения</h3>
              <span className="count">{items.length}</span>
            </div>
            {items.map((item) => (
              <AnonymousSolutionCard
                key={item.id}
                submission={item}
                active={item.id === s.id}
                onClick={() => {
                  setSelected(item.id);
                  action.clear();
                }}
              />
            ))}
          </aside>
          <div className="stack">
            <section className="panel solution-detail">
              <div className="section-heading">
                <span className="eyebrow">
                  {s.anonymous ? s.label : s.teamName}
                </span>
                {s.status === "WINNER" && (
                  <span className="pill winner-pill">
                    <Trophy size={14} />
                    Победитель
                  </span>
                )}
              </div>
              <h2>{s.title}</h2>
              <p className="lead">{s.summary}</p>
              <h3>Как решена задача</h3>
              <p>{s.solutionDescription}</p>
              <h3>Реализация</h3>
              <p>{s.implementationDetails}</p>
              {!s.anonymous && (
                <div className="revealed">
                  <h3>
                    <Users size={19} />
                    Команда {s.teamName}
                  </h3>
                  {s.members?.map((m) => (
                    <div key={m.id} className="revealed-member">
                      <strong>{m.fullName}</strong>
                      <span>{m.university}</span>
                      <a href={`mailto:${m.email}`}>{m.email}</a>
                      {m.githubUrl && (
                        <a href={m.githubUrl} target="_blank" rel="noreferrer">
                          GitHub <ArrowUpRight size={13} />
                        </a>
                      )}
                    </div>
                  ))}
                  <div className="button-row">
                    {s.demoUrl && (
                      <a
                        className="button secondary"
                        href={s.demoUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Открыть демо <ArrowUpRight size={15} />
                      </a>
                    )}
                    {s.repositoryUrl && (
                      <a
                        className="button secondary"
                        href={s.repositoryUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Репозиторий <ArrowUpRight size={15} />
                      </a>
                    )}
                  </div>
                  {s.projectFileName && (
                    <p className="small muted">
                      Демо-вложение: {s.projectFileName} (сохранено только имя
                      файла)
                    </p>
                  )}
                </div>
              )}
              {!p.winnerSubmissionId && (
                <div className="winner-actions">
                  <button
                    className="button"
                    disabled={!expired || action.busy}
                    onClick={() => {
                      action.clear();
                      setConfirm("winner");
                    }}
                  >
                    <Trophy size={17} />
                    Выбрать победителем
                  </button>
                  <span className="small muted">
                    {expired
                      ? "Ваш выбор окончательный. AI-оценка носит рекомендательный характер."
                      : "Выбор станет доступен после дедлайна."}
                  </span>
                </div>
              )}
            </section>
            {s.aiAnalysis && <AIAnalysisPanel analysis={s.aiAnalysis} />}
            <ChatPanel key={s.id} submissionId={s.id} />
          </div>
        </div>
      ) : (
        <Empty
          title="Решения ещё не поступили"
          text="Команды смогут отправить готовые проекты до дедлайна."
        />
      )}
      {confirm && (
        <Modal
          title={
            confirm === "winner"
              ? `Выбрать ${s.label}?`
              : "Завершить приём работ?"
          }
          onClose={() => !action.busy && setConfirm(null)}
        >
          <p>
            {confirm === "winner"
              ? `Are you sure you want to select ${s.label} as the winner? This action finalizes the task.`
              : "Демо-инструмент перенесёт дедлайн на текущий момент. Отправка и редактирование решений закроются, а выбор победителя станет доступен."}
          </p>
          <p className="muted">
            {confirm === "winner"
              ? "Изменить победителя будет нельзя. Данные всех команд раскроются сразу после подтверждения."
              : "Это действие сохраняется в истории задачи. Приём нельзя будет открыть заново."}
          </p>
          <ErrorBox error={action.error} />
          <div className="button-row end">
            <button
              className="button secondary"
              disabled={action.busy}
              onClick={() => setConfirm(null)}
            >
              Отмена
            </button>
            <button
              className="button"
              disabled={action.busy}
              onClick={() => void action.run(confirmAction)}
            >
              {action.busy ? "Сохраняем…" : "Подтвердить"}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
