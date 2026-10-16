import { Add, User } from "@carbon/icons-react";
import {
  Alert,
  Button,
  Card,
  Input,
  Label,
  TextField,
  toast,
} from "@heroui/react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthProvider";
import { AdminApiError, createCustomerAccount } from "./adminApi";

type UserAccountPanelProps = {
  onCreated?: () => void;
};

export function UserAccountPanel({ onCreated }: UserAccountPanelProps) {
  const { session } = useAuth();
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isPending, setIsPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsPending(true);
    try {
      await createCustomerAccount(
        { email: email.trim(), full_name: name.trim(), password },
        session!.access_token,
      );
      setEmail("");
      setName("");
      setPassword("");
      toast.success(t("customerAccount.userCreated"));
      onCreated?.();
    } catch (caught) {
      setError(
        caught instanceof AdminApiError
          ? caught.message
          : t("customerAccount.userCreateFailed"),
      );
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <Card.Header className="flex items-start gap-3 border-b border-slate-100 px-6 py-5">
        {/* <User size={20} className="text-slate-600" /> */}
        <div>
          <Card.Title className="text-lg text-slate-950">
            {t("customerAccount.createAccount")}
          </Card.Title>
          <Card.Description className="text-sm text-slate-500">
            {t("customerAccount.userAccountsDescription")}
          </Card.Description>
        </div>
      </Card.Header>
      <Card.Content className="p-6">
        <form className="grid gap-5 md:grid-cols-3" onSubmit={submit}>
          {error ? (
            <Alert className="md:col-span-3" status="danger">
              <Alert.Title>{t("customerAccount.userCreateFailed")}</Alert.Title>
              <Alert.Description>{error}</Alert.Description>
            </Alert>
          ) : null}
          <TextField isRequired name="customer-name">
            <Label>{t("customerAccount.userFullName")}</Label>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </TextField>
          <TextField isRequired name="customer-email" type="email">
            <Label>{t("auth.email")}</Label>
            <Input
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </TextField>
          <TextField isRequired name="customer-password" type="password">
            <Label>{t("auth.password")}</Label>
            <Input
              minLength={6}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </TextField>
          <div className="md:col-span-3 flex justify-end">
            <Button isPending={isPending} type="submit" variant="primary">
              <Add size={18} />
              {t("customerAccount.createUser")}
            </Button>
          </div>
        </form>
      </Card.Content>
    </Card>
  );
}
