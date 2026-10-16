import { User } from "@carbon/icons-react";
import { Alert, Card, Chip, EmptyState, Skeleton } from "@heroui/react";
import { useTranslation } from "react-i18next";

import { UserAccountPanel } from "./UserAccountPanel";
import {
  useCustomerAccounts,
  useRefreshCustomerAccounts,
} from "./useCustomerAccounts";

export function CustomerAccountsPage() {
  const { t } = useTranslation();
  const accounts = useCustomerAccounts();
  const refreshAccounts = useRefreshCustomerAccounts();

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6">
      <header className="border-b border-slate-200 pb-5">
        <div className="flex items-center gap-3 text-slate-500">
          <p className="text-sm font-semibold">
            {t("customerAccount.eyebrow")}
          </p>
        </div>
        <h1 className="mt-3 text-3xl font-semibold text-slate-950">
          {t("customerAccount.pageTitle")}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          {t("customerAccount.pageDescription")}
        </p>
      </header>

      <UserAccountPanel onCreated={() => void refreshAccounts()} />

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="border-b border-slate-100 px-6 py-5">
          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("customerAccount.listTitle")}
            </Card.Title>
            <Card.Description className="mt-1 text-sm text-slate-500">
              {t("customerAccount.listDescription")}
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="p-0">
          {accounts.isPending ? (
            <Skeleton className="m-6 h-40 rounded-lg" />
          ) : null}
          {accounts.error ? (
            <Alert className="m-6" status="danger">
              <Alert.Title>{t("customerAccount.loadFailed")}</Alert.Title>
            </Alert>
          ) : null}
          {accounts.data?.length === 0 ? (
            <EmptyState className="py-14">
              <User size={28} className="text-slate-400" />
              <h2 className="mt-3 text-base font-semibold text-slate-950">
                {t("customerAccount.empty")}
              </h2>
            </EmptyState>
          ) : null}
          {accounts.data?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[38rem] text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                  <tr>
                    <th className="px-6 py-3" scope="col">
                      {t("customerAccount.userFullName")}
                    </th>
                    <th className="px-6 py-3" scope="col">
                      {t("auth.email")}
                    </th>
                    <th className="px-6 py-3" scope="col">
                      {t("customerAccount.status")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {accounts.data.map((account) => (
                    <tr key={account.email}>
                      <td className="px-6 py-4 font-medium text-slate-950">
                        {account.full_name}
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {account.email}
                      </td>
                      <td className="px-6 py-4">
                        <Chip
                          color={account.is_active ? "success" : "default"}
                          variant="soft"
                        >
                          {account.is_active
                            ? t("customerAccount.active")
                            : t("customerAccount.inactive")}
                        </Chip>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Card.Content>
      </Card>
    </div>
  );
}
