import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowDownWideNarrow,
  BriefcaseBusiness,
  Sparkles,
  CircleCheck,
  SlidersHorizontal,
} from "lucide-react";
import { api, useAuth, useResource } from "../lib/api";
import type { Problem } from "../lib/types";
import {
  Empty,
  ErrorBox,
  Loading,
  PageTitle,
  ProblemCard,
} from "../components/ui";

export default function Catalog() {
  const [industry, setIndustry] = useState("");
  const { user } = useAuth();
  const resource = useResource(
    () => api<{ items: Problem[]; industries: string[] }>("/problems"),
    "catalog",
  );
  if (!resource.data)
    return resource.error ? <ErrorBox error={resource.error} /> : <Loading />;
  const all = resource.data.items;
  const items = all.filter((p) => !industry || p.industry === industry);
  return (
    <>
      <PageTitle
        eyebrow="БИЗНЕС × ТАЛАНТЫ"
        title="Задачи с реальным смыслом"
        description="Выберите проблему бизнеса. Создайте решение, которое будет работать."
      >
        {user?.role === "COMPANY" && (
          <Link className="button" to="/company/problems/new">
            Создать задачу <ArrowRight size={17} />
          </Link>
        )}
      </PageTitle>
      <div className="catalog-banner">
        <div>
          <span className="banner-label">
            <span /> ОТКРЫТО ДЛЯ НОВЫХ ИДЕЙ
          </span>
          <h2>
            Ваш следующий проект —<br />
            чья-то реальная задача.
          </h2>
          <p>От первого вопроса до готового решения. С поддержкой AI.</p>
        </div>
        <div className="banner-facts">
          <div>
            <strong>
              {all
                .filter((p) => p.acceptingSubmissions)
                .length.toString()
                .padStart(2, "0")}
            </strong>
            <span>открытых задач</span>
          </div>
          <div>
            <strong>
              {new Set(all.map((p) => p.company.id)).size
                .toString()
                .padStart(2, "0")}
            </strong>
            <span>компаний-партнёров</span>
          </div>
        </div>
      </div>
      <div className="catalog-toolbar">
        <div className="section-heading">
          <h2>Каталог задач</h2>
          <span className="count">{items.length}</span>
        </div>
        <div className="toolbar-controls">
          <label className="filter-label">
            <SlidersHorizontal size={16} />
            <select
              aria-label="Фильтр по отрасли"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
            >
              <option value="">Все отрасли</option>
              {resource.data.industries.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <span className="sort-label">
            <ArrowDownWideNarrow size={16} />
            Сначала с высоким качеством
          </span>
        </div>
      </div>
      <ErrorBox error={resource.error} />
      {items.length ? (
        <div className="problem-grid">
          {items.map((p) => (
            <ProblemCard problem={p} key={p.id} />
          ))}
        </div>
      ) : (
        <Empty title="В этой отрасли пока нет задач" />
      )}
      <div className="catalog-principles">
        <span>
          <BriefcaseBusiness size={17} /> Реальные задачи бизнеса
        </span>
        <span>
          <Sparkles size={17} /> AI помогает разобраться
        </span>
        <span>
          <CircleCheck size={17} /> Победителя выбирает компания
        </span>
      </div>
    </>
  );
}
