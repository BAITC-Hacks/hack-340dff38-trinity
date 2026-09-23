import { Link } from "react-router-dom";
import { Github, GraduationCap, Sparkles, ArrowUpRight } from "lucide-react";
import { api, useAuth, useResource } from "../lib/api";
import type { Points, Profile } from "../lib/types";
import { Empty, ErrorBox, Loading, PageTitle, date } from "../components/ui";

export default function StudentProfile() {
  const { user } = useAuth();
  const r = useResource(
    () =>
      Promise.all([
        api<Profile>("/students/me"),
        api<Points>("/students/me/points"),
      ]),
    `profile-${user?.id}`,
  );
  if (!r.data) return r.error ? <ErrorBox error={r.error} /> : <Loading />;
  const [p, points] = r.data;
  return (
    <>
      <PageTitle eyebrow="ПРОФИЛЬ СТУДЕНТА" title="Ваш опыт в проектах" />
      <div className="profile-layout">
        <section className="panel">
          <div className="profile-avatar">
            {p.fullName
              .split(" ")
              .map((s) => s[0])
              .join("")}
          </div>
          <h2>{p.fullName}</h2>
          <p className="muted">{p.specialization}</p>
          <div className="profile-line">
            <GraduationCap size={18} />
            {p.university} · {p.course} курс
          </div>
          <p>{p.email}</p>
          {p.githubUrl && (
            <a
              className="text-link"
              href={p.githubUrl}
              target="_blank"
              rel="noreferrer"
            >
              <Github size={17} />
              GitHub <ArrowUpRight size={14} />
            </a>
          )}
          <h4>Навыки</h4>
          <div className="tags">
            {p.skills.map((s) => (
              <span className="pill" key={s}>
                {s}
              </span>
            ))}
          </div>
          <h4>Интересы</h4>
          <div className="tags">
            {p.interests.map((s) => (
              <span className="pill" key={s}>
                {s}
              </span>
            ))}
          </div>
        </section>
        <div className="stack">
          <div className="points-hero">
            <div className="eyebrow">
              <Sparkles size={17} />
              ЛИЧНЫЙ РЕЗУЛЬТАТ
            </div>
            <strong>
              {points.totalPoints}
              <span>баллов</span>
            </strong>
            <p>
              Оценка компании делится поровну между участниками
              команды-победителя. Баллы сохраняются и накапливаются.
            </p>
          </div>
          <section className="panel">
            <h2>История начислений</h2>
            {points.transactions.length ? (
              points.transactions.map((t) => (
                <div className="transaction" key={t.id}>
                  <div>
                    <Link to={`/problems/${t.problemId}`}>
                      {t.problemTitle}
                    </Link>
                    <p className="small muted">
                      {date(t.createdAt)} · {t.reason}
                    </p>
                  </div>
                  <strong>+{t.points}</strong>
                </div>
              ))
            ) : (
              <Empty
                title="Начислений пока нет"
                text="Баллы появятся после победы и оценки компании."
              />
            )}
          </section>
        </div>
      </div>
    </>
  );
}
