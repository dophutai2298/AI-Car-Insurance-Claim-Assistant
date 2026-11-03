import { useState, type FormEvent } from "react";
import { ArrowRight, Locked } from "@carbon/icons-react";
import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

import { Brand } from "../../components/Brand";
import { ThemeToggle } from "../../components/ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";

import { AuthApiError } from "./authApi";
import { useAuth } from "./AuthProvider";

export function LoginPage() {
  const { login, session } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isPending, setIsPending] = useState(false);

  if (session)
    return (
      <Navigate
        replace
        to={session.user.role === "USER" ? "/my-claims" : "/dashboard"}
      />
    );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsPending(true);
    try {
      const nextSession = await login({ email, password });
      const requestedPath = (location.state as { from?: string } | null)?.from;
      navigate(
        requestedPath &&
          requestedPath !== "/login" &&
          (nextSession.user.role !== "USER" ||
            requestedPath.startsWith("/my-claims") ||
            requestedPath === "/claims/new")
          ? requestedPath
          : nextSession.user.role === "USER"
            ? "/my-claims"
            : "/dashboard",
        {
          replace: true,
        },
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof AuthApiError
          ? caughtError.message
          : t("auth.unableToSignIn"),
      );
    } finally {
      setIsPending(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-visual">
        <img
          className="login-visual__image"
          src="/images/claims-vehicle.jpg"
          alt=""
        />
        <Brand />
        <div className="login-visual__copy">
          <p>{t("auth.workspace")}</p>
          <h2>{t("auth.headline")}</h2>
          <p>{t("auth.description")}</p>
        </div>
      </section>
      <section className="login-workspace">
        <div className="login-controls">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
        <div className="login-form">
          <div className="lg:hidden">
            <Brand />
          </div>
          <div className="mb-5 flex size-11 items-center justify-center rounded-lg border border-slate-200 bg-white text-blue-700">
            <Locked size={21} aria-hidden="true" />
          </div>
          <h1>{t("auth.signInTitle")}</h1>
          <p>{t("auth.signInDescription")}</p>
          <form className="grid gap-5" onSubmit={handleSubmit}>
            {error ? (
              <Alert status="danger">
                <Alert.Content>
                  <Alert.Title>{t("auth.signInFailed")}</Alert.Title>
                  <Alert.Description>{error}</Alert.Description>
                </Alert.Content>
              </Alert>
            ) : null}
            <TextField fullWidth isRequired name="email" type="email">
              <Label>{t("auth.email")}</Label>
              <Input
                autoComplete="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder={t("auth.emailPlaceholder")}
                value={email}
              />
            </TextField>
            <TextField fullWidth isRequired name="password" type="password">
              <Label>{t("auth.password")}</Label>
              <Input
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                value={password}
              />
            </TextField>
            <Button
              className="mt-2 w-full"
              isPending={isPending}
              type="submit"
              variant="primary"
            >
              {t("auth.signIn")}
              <ArrowRight size={18} />
            </Button>
          </form>
        </div>
        <p className="login-footnote">{t("auth.authorizedOnly")}</p>
      </section>
    </main>
  );
}
