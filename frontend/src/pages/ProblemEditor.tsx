import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Save,
  Send,
  CalendarDays,
  Check,
} from "lucide-react";
import { api, useAction } from "../lib/api";
import type {
  Advice,
  Analysis,
  Card,
  Company,
  Interview,
  Problem,
} from "../lib/types";
import { ErrorBox, PageTitle, ScoreBreakdown, Loading } from "../components/ui";

const blank: Card = {
  title: "",
  context: "",
  need: "",
  users: "",
  availableData: "",
  constraints: "",
  expectedResult: "",
  successCriteria: "",
  businessContact: "",
  interactionFormat: "",
  industry: "",
};
const fields: [keyof Card, string, string][] = [
  ["context", "Контекст", "Что происходит сейчас? Как устроен процесс?"],
  ["need", "Потребность бизнеса", "Что нужно изменить и почему это важно?"],
  ["users", "Пользователи", "Кто и как будет пользоваться решением?"],
  [
    "availableData",
    "Данные и материалы",
    "Источники, формат, поля и способ доступа",
  ],
  [
    "constraints",
    "Ограничения",
    "Технологии, ресурсы, бюджет и правила работы с данными",
  ],
  [
    "expectedResult",
    "Ожидаемый результат",
    "Какой готовый проект должна сдать команда?",
  ],
  [
    "successCriteria",
    "Критерии успеха",
    "Метрики, целевые значения и способ проверки",
  ],
  [
    "businessContact",
    "Связь с бизнесом",
    "К кому обращаться за данными и уточнениями?",
  ],
  [
    "interactionFormat",
    "Формат взаимодействия",
    "Встречи, обратная связь и доступность представителя",
  ],
];
const localDate = (iso: string) => {
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
};

export default function ProblemEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const action = useAction();
  const [step, setStep] = useState(id ? 3 : 1);
  const [loading, setLoading] = useState(!!id);
  const [loadError, setLoadError] = useState("");
  const [description, setDescription] = useState("");
  const [interview, setInterview] = useState<Interview | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [card, setCard] = useState<Card>(blank);
  const [deadline, setDeadline] = useState(
    localDate(new Date(Date.now() + 14 * 86400000).toISOString()),
  );
  const [score, setScore] = useState<Analysis | null>(null);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [scoreStale, setScoreStale] = useState(false);
  useEffect(() => {
    if (id)
      api<Problem>(`/problems/${id}`)
        .then((p) => {
          setProblem(p);
          setCard(
            Object.fromEntries(
              Object.keys(blank).map((k) => [k, p[k as keyof Card]]),
            ) as Card,
          );
          setDeadline(localDate(p.deadline));
          setScore(p.qualityAnalysis);
        })
        .catch((e) => setLoadError(e.message))
        .finally(() => setLoading(false));
    else
      api<Company>("/company/me")
        .then((c) =>
          setCard((v) => ({
            ...v,
            industry: c.industry,
            businessContact: c.email,
          })),
        )
        .catch((e) => setLoadError(e.message));
  }, [id]);
  const update = (key: keyof Card, value: string) => {
    setCard((c) => ({ ...c, [key]: value }));
    setScoreStale(true);
  };
  async function analyze() {
    const result = await api<Interview>("/ai/problem/analyze", "POST", {
      description,
      answers,
    });
    setInterview(result);
    setStep(2);
  }
  async function formCard() {
    const result = await api<Interview>("/ai/problem/analyze", "POST", {
      description,
      answers,
    });
    const next = {
      ...result.draft,
      industry: result.draft.industry || card.industry,
      businessContact: result.draft.businessContact || card.businessContact,
    };
    setCard(next);
    setStep(3);
    const [quality, recommendation] = await Promise.all([
      api<Analysis>("/ai/problem/score", "POST", next),
      api<Advice>("/ai/deadline/recommend", "POST", next),
    ]);
    setScore(quality);
    setAdvice(recommendation);
    setScoreStale(false);
  }
  async function save(publish: boolean) {
    const p = await api<Problem>(
      id ? `/problems/${id}` : "/problems",
      id ? "PATCH" : "POST",
      { ...card, deadline: new Date(deadline).toISOString() },
    );
    if (publish) await api(`/problems/${p.id}/publish`, "POST");
    navigate(`/problems/${p.id}`);
  }
  if (loading) return <Loading />;
  return (
    <>
      <Link className="back-link" to="/company/dashboard">
        <ArrowLeft size={16} />
        Кабинет компании
      </Link>
      <PageTitle
        eyebrow="AI-АССИСТЕНТ БИЗНЕСА"
        title={id ? "Уточним задачу" : "Хорошее решение начинается с вопроса"}
        description="Расскажите о проблеме. Мы поможем сделать её понятной для команды."
      />
      <div className="steps">
        {["Опишите проблему", "Уточните детали", "Проверьте и опубликуйте"].map(
          (s, i) => (
            <div className={step >= i + 1 ? "current" : ""} key={s}>
              <span>{step > i + 1 ? <Check size={15} /> : i + 1}</span>
              {s}
            </div>
          ),
        )}
      </div>
      <ErrorBox error={loadError} />
      <ErrorBox error={action.error} />
      {step === 1 && (
        <section className="panel interview-intro">
          <span className="feature-icon">
            <Sparkles size={24} />
          </span>
          <h2>С чем сталкивается ваш бизнес?</h2>
          <p className="muted">
            Начните своими словами. Даже короткого описания достаточно для
            первого шага.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action.run(analyze);
            }}
          >
            <label className="sr-only" htmlFor="description">
              Описание проблемы
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="У нас магазин одежды, и мы хотим уменьшить количество возвратов интернет-заказов…"
              minLength={10}
              maxLength={8000}
              required
              rows={5}
            />
            <div className="button-row spread">
              <button
                type="button"
                className="text-link"
                onClick={() =>
                  setDescription(
                    "У нас магазин одежды, и мы хотим уменьшить количество возвратов интернет-заказов.",
                  )
                }
              >
                Использовать пример
              </button>
              <button className="button" disabled={action.busy}>
                <Sparkles size={17} />
                {action.busy ? "Анализируем…" : "Разобрать с AI"}
              </button>
            </div>
          </form>
          <p className="small muted">
            AI не придумывает факты. Недостающие сведения останутся пустыми.
          </p>
        </section>
      )}
      {step === 2 && interview && (
        <section className="panel">
          <div className="section-heading">
            <h2>Давайте добавим конкретики</h2>
            <span className="pill">
              {interview.source === "claude" ? "Claude" : "Демо AI"}
            </span>
          </div>
          <p className="muted">
            Ответьте на известные вопросы. Остальное можно уточнить при
            редактировании карточки.
          </p>
          <div className="question-form">
            {interview.questions.map((q, i) => (
              <label key={q.id}>
                <span className="question-number">
                  {String(i + 1).padStart(2, "0")}
                </span>
                {q.question}
                <textarea
                  rows={3}
                  maxLength={4000}
                  value={answers[q.id] || ""}
                  onChange={(e) =>
                    setAnswers((a) => ({ ...a, [q.id]: e.target.value }))
                  }
                  placeholder="Ваш ответ"
                />
              </label>
            ))}
          </div>
          <div className="button-row spread">
            <button
              className="button secondary"
              onClick={() => setStep(1)}
              disabled={action.busy}
            >
              Назад
            </button>
            <button
              className="button"
              onClick={() => void action.run(formCard)}
              disabled={action.busy}
            >
              {action.busy ? "Формируем карточку…" : "Сформировать карточку"}
              <ArrowRight size={17} />
            </button>
          </div>
        </section>
      )}
      {step === 3 && (
        <div className="editor-layout">
          <form
            id="problem-form"
            className="panel form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              const submitter = (e.nativeEvent as SubmitEvent)
                .submitter as HTMLButtonElement;
              void action.run(() => save(submitter?.value === "publish"));
            }}
          >
            {problem && problem.submissionCount > 0 && (
              <div className="notice">
                Уже получено {problem.submissionCount} решений. Изменения
                сохранятся в истории и будут видны студентам.
              </div>
            )}
            <label>
              Название задачи
              <input
                required
                minLength={3}
                maxLength={180}
                value={card.title}
                onChange={(e) => update("title", e.target.value)}
              />
            </label>
            <label>
              Отрасль
              <input
                required
                maxLength={120}
                value={card.industry}
                onChange={(e) => update("industry", e.target.value)}
                placeholder="Например, Retail или Logistics"
              />
            </label>
            {fields.map(([key, title, placeholder]) => (
              <label key={key}>
                {title}
                <textarea
                  rows={3}
                  maxLength={8000}
                  value={card[key]}
                  onChange={(e) => update(key, e.target.value)}
                  placeholder={placeholder}
                />
              </label>
            ))}
            <label>
              Дедлайн приёма решений
              <input
                type="datetime-local"
                required
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
              <span className="small muted">
                В вашем часовом поясе. Окончательный срок выбираете вы.
              </span>
            </label>
            <div className="button-row">
              <button
                className="button secondary"
                type="submit"
                value="draft"
                disabled={action.busy}
              >
                <Save size={17} />
                {id ? "Сохранить изменения" : "Сохранить черновик"}
              </button>
              {(!problem || problem.status === "DRAFT") && (
                <button
                  className="button"
                  type="submit"
                  value="publish"
                  disabled={action.busy}
                >
                  <Send size={16} />
                  {action.busy ? "Сохраняем…" : "Подтвердить и опубликовать"}
                </button>
              )}
            </div>
          </form>
          <aside className="stack">
            <section className="panel">
              {score ? (
                <ScoreBreakdown analysis={score} />
              ) : (
                <>
                  <h3>Качество задачи</h3>
                  <p className="muted">
                    Проверьте полноту постановки перед публикацией.
                  </p>
                </>
              )}
              {scoreStale && (
                <p className="small muted">
                  Карточка изменена. При сохранении оценка обновится.
                </p>
              )}
              <button
                className="button secondary full"
                disabled={action.busy}
                onClick={() =>
                  void action.run(async () => {
                    setScore(
                      await api<Analysis>("/ai/problem/score", "POST", card),
                    );
                    setScoreStale(false);
                  })
                }
              >
                <Sparkles size={16} />
                Пересчитать качество
              </button>
            </section>
            <section className="panel deadline-advice">
              <CalendarDays size={25} />
              <h3>Сколько времени нужно?</h3>
              {advice && (
                <>
                  <div className="advice-days">
                    {advice.days}
                    <span>дней рекомендует AI</span>
                  </div>
                  <p>{advice.reason}</p>
                  <button
                    type="button"
                    className="text-link"
                    onClick={() =>
                      setDeadline(
                        localDate(
                          new Date(
                            Date.now() + advice.days * 86400000,
                          ).toISOString(),
                        ),
                      )
                    }
                  >
                    Использовать этот срок <ArrowRight size={14} />
                  </button>
                </>
              )}
              <button
                className="button secondary full"
                disabled={action.busy}
                onClick={() =>
                  void action.run(async () =>
                    setAdvice(
                      await api<Advice>("/ai/deadline/recommend", "POST", card),
                    ),
                  )
                }
              >
                Получить рекомендацию
              </button>
            </section>
          </aside>
        </div>
      )}
    </>
  );
}
