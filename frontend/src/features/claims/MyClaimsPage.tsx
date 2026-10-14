import { Add, ArrowRight, Document } from "@carbon/icons-react";
import { Alert, Button, Card, Chip, EmptyState, Skeleton } from "@heroui/react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { statusTone } from "./statusPresentation";
import { useMyClaims } from "./useClaims";

export function MyClaimsPage() {
  const { i18n, t } = useTranslation();
  const navigate = useNavigate();
  const { data, error, isPending } = useMyClaims();

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            {t("myClaims.eyebrow")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {t("myClaims.title")}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t("myClaims.description")}
          </p>
        </div>
        <Button onPress={() => navigate("/claims/new")} variant="primary">
          <Add size={18} />
          {t("myClaims.newClaim")}
        </Button>
      </header>

      {error ? (
        <Alert status="danger">
          <Alert.Title>{t("myClaims.loadFailed")}</Alert.Title>
        </Alert>
      ) : null}
      {isPending ? <Skeleton className="h-48 rounded-lg" /> : null}
      {data && data.length === 0 ? (
        <EmptyState className="border border-slate-200 bg-white py-16">
          <Document size={28} className="text-slate-400" />
          <h2 className="mt-3 text-base font-semibold text-slate-950">
            {t("myClaims.empty")}
          </h2>
        </EmptyState>
      ) : null}
      {data && data.length > 0 ? (
        <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <Card.Content className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
                <tr>
                  <th className="px-5 py-3">{t("myClaims.claim")}</th>
                  <th className="px-5 py-3">{t("myClaims.created")}</th>
                  <th className="px-5 py-3">{t("myClaims.status")}</th>
                  <th className="px-5 py-3 text-right">
                    {t("myClaims.action")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((claim) => (
                  <tr key={claim.id}>
                    <td className="px-5 py-4 font-semibold text-slate-950">
                      {claim.id}
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {new Date(claim.created_at).toLocaleDateString(
                        i18n.language,
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <Chip color={statusTone[claim.status]} variant="soft">
                        {t(`claim.status.${claim.status}`)}
                      </Chip>
                    </td>
                    <td className="px-5 py-4 text-right">
                      {claim.status === "DRAFT" ? (
                        <Link
                          className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:text-blue-900"
                          to={`/my-claims/${claim.id}/edit`}
                        >
                          {t("myClaims.continue")}
                          <ArrowRight size={16} />
                        </Link>
                      ) : (
                        <span className="text-slate-400">
                          {t("myClaims.submitted")}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card.Content>
        </Card>
      ) : null}
    </div>
  );
}
