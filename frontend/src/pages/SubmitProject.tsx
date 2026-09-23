import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  Send,
  Upload,
  ShieldCheck,
  Save,
  Users,
} from "lucide-react";
import { api, useAction, useResource } from "../lib/api";
import type { Problem, Submission, Team } from "../lib/types";
import {
  AIAnalysisPanel,
  ChatPanel,
  DeadlineBadge,
  ErrorBox,
  Loading,
  PageTitle,
} from "../components/ui";

interface Form {
  teamId: number;
  title: string;
  summary: string;
  solutionDescription: string;
  implementationDetails: string;
  demoUrl: string;
  repositoryUrl: string;
  projectFileName: string;
}
const blank: Form = {
  teamId: 0,
  title: "",
  summary: "",
  solutionDescription: "",
  implementationDetails: "",
  demoUrl: "",
  repositoryUrl: "",
  projectFileName: "",
};

export default function SubmitProject() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const submissionId = params.get("submission");
  const action = useAction();
  const r = useResource(
    () =>
      Promise.all([
        api<Problem>(`/problems/${id}`),
        api<Team[]>("/teams"),
        submissionId
          ? api<Submission>(`/submissions/${submissionId}`)
          : Promise.resolve(null),
      ]),
    `submit-${id}-${submissionId}`,
  );
  const [form, setForm] = useState<Form>(blank);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (r.data) {
      const [, teams, s] = r.data;
      setForm(
        s
          ? {
              teamId: s.teamId!,
              title: s.title,
              summary: s.summary,
              solutionDescription: s.solutionDescription,
              implementationDetails: s.implementationDetails,
              demoUrl: s.demoUrl || "",
              repositoryUrl: s.repositoryUrl || "",
              projectFileName: s.projectFileName || "",
            }
          : { ...blank, teamId: teams[0]?.id || 0 },
      );
    }
  }, [r.data]);
  if (!r.data) return r.error ? <ErrorBox error={r.error} /> : <Loading />;
  const [p, teams, s] = r.data;
  const open =
    p.acceptingSubmissions && new Date(p.deadline).getTime() > Date.now();
  const update = (key: keyof Form, value: string | number) => {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  };
  return (
    <>
      <Link className="back-link" to={`/problems/${id}`}>
        <ArrowLeft size={16} />К задаче
      </Link>
      <PageTitle
        eyebrow={p.company.name.toUpperCase()}
        title={s ? "Ваш проект" : "Время показать решение"}
        description={p.title}
      >
        <DeadlineBadge deadline={p.deadline} />
      </PageTitle>
      <ErrorBox error={r.error} />
      <ErrorBox error={action.error} />
      {saved && (
        <div className="notice success" role="status">
          Решение сохранено. AI-анализ готов, компания может изучить работу.
        </div>
      )}
      {!open && (
        <div className="notice">
          Дедлайн завершён. Отправка и редактирование заблокированы; обсуждение
          остаётся доступным.
        </div>
      )}
      <div className="editor-layout">
        <form
          className="panel form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => {
              const result = await api<Submission>(
                s ? `/submissions/${s.id}` : `/problems/${id}/submissions`,
                s ? "PATCH" : "POST",
                form,
              );
              setSaved(true);
              if (s) r.reload();
              else setParams({ submission: result.id });
            });
          }}
        >
          <fieldset disabled={!open || action.busy}>
            <label>
              Команда
              <select
                required
                value={form.teamId || ""}
                disabled={!!s}
                onChange={(e) => update("teamId", Number(e.target.value))}
              >
                <option value="">Выберите команду</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} · {t.members.length} участников
                  </option>
                ))}
              </select>
            </label>
            {!teams.length && (
              <Link className="text-link" to="/student/dashboard">
                Сначала создайте команду в кабинете <Users size={16} />
              </Link>
            )}
            <label>
              Название проекта
              <input
                required
                minLength={3}
                maxLength={180}
                value={form.title}
                onChange={(e) => update("title", e.target.value)}
                placeholder="Короткое название вашего решения"
              />
            </label>
            <label>
              Краткое описание
              <textarea
                required
                minLength={10}
                maxLength={3000}
                rows={3}
                value={form.summary}
                onChange={(e) => update("summary", e.target.value)}
                placeholder="Какую проблему решает проект и в чём его ценность?"
              />
            </label>
            <label>
              Описание решения
              <textarea
                required
                minLength={20}
                maxLength={12000}
                rows={6}
                value={form.solutionDescription}
                onChange={(e) => update("solutionDescription", e.target.value)}
                placeholder="Подход, сценарии использования, результаты и соответствие задаче"
              />
            </label>
            <label>
              Техническая реализация
              <textarea
                required
                minLength={20}
                maxLength={12000}
                rows={6}
                value={form.implementationDetails}
                onChange={(e) =>
                  update("implementationDetails", e.target.value)
                }
                placeholder="Стек, архитектура, запуск, тестирование и известные ограничения"
              />
            </label>
            <div className="form-columns">
              <label>
                Ссылка на демо
                <input
                  type="url"
                  maxLength={1000}
                  value={form.demoUrl}
                  onChange={(e) => update("demoUrl", e.target.value)}
                  placeholder="https://…"
                />
              </label>
              <label>
                Репозиторий
                <input
                  type="url"
                  maxLength={1000}
                  value={form.repositoryUrl}
                  onChange={(e) => update("repositoryUrl", e.target.value)}
                  placeholder="https://…"
                />
              </label>
            </div>
            <label className="upload-area">
              <Upload size={24} />
              <strong>Прикрепить файл проекта</strong>
              <span className="small muted">
                Демо-вложение: сохраняется только имя файла, содержимое не
                загружается.
              </span>
              <input
                type="file"
                aria-label="Файл проекта (демо)"
                onChange={(e) =>
                  update("projectFileName", e.target.files?.[0]?.name || "")
                }
              />
              {form.projectFileName && <span>{form.projectFileName}</span>}
            </label>
            {open && (
              <button className="button" disabled={!form.teamId || action.busy}>
                {s ? <Save size={17} /> : <Send size={17} />}{" "}
                {action.busy
                  ? "Сохраняем и анализируем…"
                  : s
                    ? "Сохранить и обновить анализ"
                    : "Отправить готовый проект"}
              </button>
            )}
          </fieldset>
        </form>
        <aside className="stack">
          <section className="panel privacy-panel">
            <ShieldCheck size={28} />
            <h3>Идея важнее имени</h3>
            <p>
              До выбора победителя бизнес видит решение анонимно. Профили,
              контакты, внешние ссылки и имена файлов раскроются после выбора.
            </p>
            <p className="small muted">
              Не включайте имена авторов, название команды и другие
              идентификаторы в текст проекта или сообщения.
            </p>
          </section>
          {s && <ChatPanel submissionId={s.id} />}
        </aside>
      </div>
      {s?.aiAnalysis && (
        <div className="section-space">
          <AIAnalysisPanel analysis={s.aiAnalysis} />
        </div>
      )}
    </>
  );
}
