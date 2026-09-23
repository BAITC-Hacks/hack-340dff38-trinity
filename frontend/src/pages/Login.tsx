import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  GraduationCap,
  Building2,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { api, useAction, useAuth, useResource } from "../lib/api";
import type { Role, User } from "../lib/types";
import { ErrorBox, Loading, PageTitle } from "../components/ui";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const action = useAction();
  const [role, setRole] = useState<Role>("STUDENT");
  const [account, setAccount] = useState(0);
  const [code, setCode] = useState("");
  const resource = useResource(
    () =>
      api<{ accounts: User[]; accessCodeRequired: boolean }>(
        "/auth/demo-accounts",
      ),
    "accounts",
  );
  if (!resource.data)
    return resource.error ? <ErrorBox error={resource.error} /> : <Loading />;
  const accounts = resource.data.accounts.filter((a) => a.role === role);
  return (
    <div className="login-page">
      <PageTitle
        eyebrow="ДОБРО ПОЖАЛОВАТЬ В AI SANA"
        title="С какой стороны начнём?"
        description="Выберите роль и исследуйте полный путь от задачи до результата."
      />
      <div className="role-grid">
        {(
          [
            {
              role: "STUDENT",
              title: "Я студент",
              text: "Создавайте проекты, работайте в команде и решайте задачи бизнеса.",
              Icon: GraduationCap,
            },
            {
              role: "COMPANY",
              title: "Я представляю бизнес",
              text: "Сформулируйте задачу с AI и найдите подходящее решение.",
              Icon: Building2,
            },
            {
              role: "ADMIN",
              title: "Я администратор",
              text: "Проверяйте отмеченный контент и управляйте модерацией.",
              Icon: ShieldCheck,
            },
          ] as const
        ).map((r) => (
          <button
            className={`role-card ${role === r.role ? "selected" : ""}`}
            key={r.role}
            onClick={() => {
              setRole(r.role);
              setAccount(0);
            }}
          >
            <r.Icon size={28} />
            <h3>{r.title}</h3>
            <p>{r.text}</p>
            <span>
              {role === r.role ? "Выбрано" : "Выбрать роль"}{" "}
              <ArrowRight size={16} />
            </span>
          </button>
        ))}
      </div>
      <form
        className="panel login-form"
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(async () => {
            const result = await api<{ token: string; user: User }>(
              "/auth/demo-login",
              "POST",
              { userId: account || accounts[0].id, accessCode: code },
            );
            localStorage.setItem("sana-token", result.token);
            setUser(result.user);
            navigate(
              role === "COMPANY"
                ? "/company/dashboard"
                : role === "STUDENT"
                  ? "/student/dashboard"
                  : "/admin",
            );
          });
        }}
      >
        <label>
          Демо-аккаунт
          <select
            value={account || accounts[0]?.id}
            onChange={(e) => setAccount(Number(e.target.value))}
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} · {a.email}
              </option>
            ))}
          </select>
        </label>
        {resource.data.accessCodeRequired && (
          <label>
            Код доступа
            <input
              type="password"
              autoComplete="current-password"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </label>
        )}
        <ErrorBox error={action.error} />
        <button className="button" disabled={action.busy}>
          {action.busy ? "Входим…" : "Продолжить"}
          <ArrowRight size={18} />
        </button>
        <p className="small muted">
          Демонстрационные аккаунты и синтетические данные. Все роли можно
          переключать в меню профиля.
        </p>
      </form>
    </div>
  );
}
