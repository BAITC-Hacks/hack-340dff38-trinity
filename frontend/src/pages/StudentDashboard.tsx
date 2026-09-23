import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  ArrowUpRight,
  Users,
  Trophy,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { api, useAction, useAuth, useResource } from "../lib/api";
import type { Member, Profile, Submission, Team } from "../lib/types";
import {
  ChatPanel,
  Empty,
  ErrorBox,
  Loading,
  Modal,
  PageTitle,
  SubmissionCard,
} from "../components/ui";

export default function StudentDashboard() {
  const { user } = useAuth();
  const action = useAction();
  const r = useResource(
    () =>
      Promise.all([
        api<Profile>("/students/me"),
        api<Team[]>("/teams"),
        api<Submission[]>("/students/me/submissions"),
        api<Member[]>("/students/demo-directory"),
      ]),
    `student-${user?.id}`,
  );
  const [tab, setTab] = useState("submissions");
  const [create, setCreate] = useState(false);
  const [name, setName] = useState("");
  const [members, setMembers] = useState<number[]>([]);
  const [chat, setChat] = useState<string | null>(null);
  const [addTeam, setAddTeam] = useState<Team | null>(null);
  const [newMember, setNewMember] = useState("");
  if (!r.data) return r.error ? <ErrorBox error={r.error} /> : <Loading />;
  const [profile, teams, submissions, directory] = r.data;
  const shown =
    tab === "wins"
      ? submissions.filter((s) => s.status === "WINNER")
      : submissions;
  return (
    <>
      <PageTitle
        eyebrow="ЛИЧНОЕ ПРОСТРАНСТВО"
        title={`Привет, ${profile.fullName.split(" ")[0]}`}
        description="Здесь ваши команды, проекты и результаты."
      >
        <Link to="/" className="button">
          Найти задачу <ArrowUpRight size={17} />
        </Link>
      </PageTitle>
      <div className="stat-grid">
        <Link to="/student/profile" className="stat accent-stat">
          <Sparkles />
          <strong>{profile.totalPoints}</strong>
          <span>
            Ваших баллов <ArrowRight size={15} />
          </span>
        </Link>
        <div className="stat">
          <Users />
          <strong>{teams.length}</strong>
          <span>Команд</span>
        </div>
        <div className="stat">
          <Trophy />
          <strong>
            {submissions.filter((s) => s.status === "WINNER").length}
          </strong>
          <span>Выигранных проектов</span>
        </div>
      </div>
      <div className="tabs" role="tablist" aria-label="Разделы кабинета">
        {[
          ["submissions", "Мои решения", submissions.length],
          ["teams", "Мои команды", teams.length],
          [
            "wins",
            "Победы",
            submissions.filter((s) => s.status === "WINNER").length,
          ],
        ].map(([id, title, count]) => (
          <button
            role="tab"
            aria-selected={tab === id}
            key={id}
            onClick={() => setTab(id as string)}
          >
            {title}
            <span>{count}</span>
          </button>
        ))}
      </div>
      <ErrorBox error={action.error} />
      {tab === "teams" ? (
        <>
          <div className="section-heading section-space">
            <h2>Вместе или соло</h2>
            <button
              className="button"
              onClick={() => {
                action.clear();
                setName("");
                setMembers([]);
                setCreate(true);
              }}
            >
              <Plus size={16} />
              Создать команду
            </button>
          </div>
          <div className="team-grid">
            {teams.map((t) => (
              <section className="panel team-card" key={t.id}>
                <div className="team-icon">
                  <Users size={24} />
                </div>
                <h3>{t.name}</h3>
                <p className="muted">
                  {t.members.length === 1
                    ? "Соло-команда"
                    : `${t.members.length} участника`}
                </p>
                <div className="avatar-row">
                  {t.members.map((m) => (
                    <span title={m.fullName} key={m.id}>
                      {m.fullName
                        .split(" ")
                        .map((s) => s[0])
                        .join("")}
                    </span>
                  ))}
                </div>
                {t.members.map((m) => (
                  <div className="team-member" key={m.id}>
                    <strong>{m.fullName}</strong>
                    <span>{m.university}</span>
                  </div>
                ))}
                {!t.locked && (
                  <button
                    className="button secondary full"
                    onClick={() => {
                      action.clear();
                      setNewMember("");
                      setAddTeam(t);
                    }}
                  >
                    Добавить участника
                  </button>
                )}
                {t.locked && (
                  <p className="small muted">
                    Состав зафиксирован после отправки проекта.
                  </p>
                )}
              </section>
            ))}
          </div>
          {teams.length === 0 && (
            <Empty
              title="Создайте свою первую команду"
              text="Можно участвовать одному или пригласить демо-участников."
            />
          )}
        </>
      ) : (
        <>
          {shown.length ? (
            <div className="submission-grid">
              {shown.map((s) => (
                <SubmissionCard submission={s} key={s.id}>
                  <div className="button-row">
                    <Link
                      className="button secondary"
                      to={`/student/problems/${s.problemId}/submit?submission=${s.id}`}
                    >
                      Открыть проект <ArrowUpRight size={15} />
                    </Link>
                    <button className="text-link" onClick={() => setChat(s.id)}>
                      Чат с бизнесом
                    </button>
                  </div>
                </SubmissionCard>
              ))}
            </div>
          ) : (
            <Empty
              title={
                tab === "wins" ? "Победы ещё впереди" : "Ваш первый проект ждёт"
              }
              text="Выберите задачу в каталоге и отправьте готовое решение."
            >
              <Link className="button" to="/">
                Открыть каталог
              </Link>
            </Empty>
          )}
        </>
      )}
      {create && (
        <Modal title="Новая команда" onClose={() => setCreate(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action.run(async () => {
                await api("/teams", "POST", { name, memberIds: members });
                setCreate(false);
                r.reload();
              });
            }}
          >
            <label>
              Название
              <input
                required
                minLength={2}
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Как назовём команду?"
              />
            </label>
            <p className="small muted">
              Вы уже в составе. Не добавляйте других участников, если хотите
              работать соло.
            </p>
            <div className="member-picker">
              {directory
                .filter((m) => m.id !== user?.id)
                .map((m) => (
                  <label key={m.id}>
                    <input
                      type="checkbox"
                      checked={members.includes(m.id)}
                      onChange={(e) =>
                        setMembers((old) =>
                          e.target.checked
                            ? [...old, m.id]
                            : old.filter((i) => i !== m.id),
                        )
                      }
                    />
                    <span>
                      <strong>{m.fullName}</strong>
                      <small>{m.university}</small>
                    </span>
                  </label>
                ))}
            </div>
            <ErrorBox error={action.error} />
            <button className="button full" disabled={action.busy}>
              Создать команду
            </button>
          </form>
        </Modal>
      )}
      {addTeam && (
        <Modal
          title={`Участники · ${addTeam.name}`}
          onClose={() => setAddTeam(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action.run(async () => {
                await api(`/teams/${addTeam.id}/members`, "POST", {
                  studentId: Number(newMember),
                });
                setAddTeam(null);
                r.reload();
              });
            }}
          >
            <label>
              Добавить демо-участника
              <select
                required
                value={newMember}
                onChange={(e) => setNewMember(e.target.value)}
              >
                <option value="">Выберите участника</option>
                {directory
                  .filter((m) => !addTeam.members.some((x) => x.id === m.id))
                  .map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.fullName}
                    </option>
                  ))}
              </select>
            </label>
            <ErrorBox error={action.error} />
            <button className="button full" disabled={action.busy}>
              Добавить
            </button>
          </form>
        </Modal>
      )}
      {chat && (
        <Modal title="Чат с бизнесом" onClose={() => setChat(null)}>
          <ChatPanel submissionId={chat} />
        </Modal>
      )}
    </>
  );
}
