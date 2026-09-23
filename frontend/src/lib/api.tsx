import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { User } from "./types";

const BASE = import.meta.env.VITE_API_URL || "/api";
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const token = localStorage.getItem("sana-token");
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (e: { loc: string[]; msg: string }) =>
                  `${e.loc.slice(1).join(".")}: ${e.msg}`,
              )
              .join("; ")
          : `Ошибка сервера (${response.status}). Повторите позже.`,
    );
  }
  return data as T;
}

export function useResource<T>(load: () => Promise<T>, key: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setError("");
    setLoading(true);
    load()
      .then((value) => {
        if (active) setData(value);
      })
      .catch((e) => {
        if (active) setError(e.message || "Не удалось загрузить данные");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // key deliberately describes the data request, not the callback identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version]);
  return { data, error, loading, reload: () => setVersion((v) => v + 1) };
}

export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(action: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось выполнить действие",
      );
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run, clear: () => setError("") };
}

interface Auth {
  user: User | null;
  ready: boolean;
  setUser: (u: User) => void;
  logout: () => void;
}
const AuthContext = createContext<Auth>({
  user: null,
  ready: false,
  setUser: () => {},
  logout: () => {},
});
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!localStorage.getItem("sana-token")) {
      setReady(true);
      return;
    }
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("sana-token"))
      .finally(() => setReady(true));
  }, []);
  return (
    <AuthContext.Provider
      value={{
        user,
        ready,
        setUser,
        logout: () => {
          localStorage.removeItem("sana-token");
          setUser(null);
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
