import { useState } from "react";
import { ShieldCheck, Check, EyeOff, AlertTriangle } from "lucide-react";
import { api, useAction, useResource } from "../lib/api";
import { Empty, ErrorBox, Loading, PageTitle } from "../components/ui";

interface Queue {
  counts: Record<string, number>;
  items: {
    id: number;
    entityType: string;
    entityId: string;
    status: string;
    reasons: string[];
    excerpt: string;
    source: string;
  }[];
}
const names: Record<string, string> = {
  problems: "Задач",
  students: "Студентов",
  companies: "Компаний",
  submissions: "Решений",
  problem: "Задача",
  submission: "Решение",
  comment: "Комментарий",
  question: "Вопрос",
  answer: "Ответ",
};
export default function Admin() {
  const r = useResource(() => api<Queue>("/admin/moderation"), "admin");
  const action = useAction();
  const [filter, setFilter] = useState("pending");
  if (!r.data) return r.error ? <ErrorBox error={r.error} /> : <Loading />;
  const flagged = r.data.items.filter((i) =>
    ["FLAGGED", "REVIEW_REQUIRED"].includes(i.status),
  );
  const items = filter === "pending" ? flagged : r.data.items;
  return (
    <>
      <PageTitle
        eyebrow="МОДЕРАЦИЯ ПЛАТФОРМЫ"
        title="Безопасное пространство для идей"
        description="AI отмечает возможные проблемы. Окончательное решение принимаете вы."
      />
      <div className="stat-grid four">
        {Object.entries(r.data.counts).map(([key, count]) => (
          <div className="stat" key={key}>
            <strong>{count}</strong>
            <span>{names[key]}</span>
          </div>
        ))}
      </div>
      <div className="catalog-toolbar">
        <div className="section-heading">
          <h2>Очередь проверки</h2>
          <span className="count">{flagged.length}</span>
        </div>
        <select
          aria-label="Статус модерации"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="pending">Требуют проверки</option>
          <option value="all">Все записи</option>
        </select>
      </div>
      <ErrorBox error={action.error} />
      <ErrorBox error={r.error} />
      {items.length ? (
        <div className="stack">
          {items.map((item) => (
            <section className="panel moderation-card" key={item.id}>
              <div className="section-heading">
                <div className="tags">
                  <span className="pill">{names[item.entityType]}</span>
                  <span
                    className={`moderation-status ${item.status === "REVIEW_REQUIRED" ? "flagged" : ""}`}
                  >
                    <AlertTriangle size={14} />
                    {item.status}
                  </span>
                </div>
                <span className="small muted">
                  {item.source === "claude" ? "Claude" : "Демо-анализ"}
                </span>
              </div>
              <p>{item.excerpt}</p>
              {item.reasons.map((reason) => (
                <p className="notice small" key={reason}>
                  {reason}
                </p>
              ))}
              <div className="button-row end">
                <button
                  className="button secondary"
                  disabled={action.busy || item.status === "HIDDEN"}
                  onClick={() =>
                    void action.run(async () => {
                      await api(`/admin/moderation/${item.id}/hide`, "POST");
                      r.reload();
                    })
                  }
                >
                  <EyeOff size={16} />
                  Скрыть
                </button>
                <button
                  className="button"
                  disabled={action.busy || item.status === "APPROVED"}
                  onClick={() =>
                    void action.run(async () => {
                      await api(`/admin/moderation/${item.id}/approve`, "POST");
                      r.reload();
                    })
                  }
                >
                  <Check size={16} />
                  Одобрить
                </button>
              </div>
            </section>
          ))}
        </div>
      ) : (
        <Empty
          title="Всё проверено"
          text="Сейчас нет материалов, ожидающих решения."
        >
          <ShieldCheck size={30} />
        </Empty>
      )}
    </>
  );
}
