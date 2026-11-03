import {
  ChartColumn,
  CheckmarkOutline,
  CloudUpload,
  Document,
  ErrorOutline,
  WarningAlt,
} from "@carbon/icons-react";
import { Button, Card, Chip, EmptyState, Skeleton, Toast } from "@heroui/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { AppShell } from "./components/AppShell";

import { ClaimQueueTable } from "./features/dashboard/ClaimQueueTable";
import { useDashboardOverview } from "./features/dashboard/useDashboardOverview";
import { LoginPage } from "./features/auth/LoginPage";
import { useAuth } from "./features/auth/AuthProvider";
import { ProtectedRoute, RoleRoute } from "./features/auth/ProtectedRoute";
import { ClaimCreatePage } from "./features/claims/ClaimCreatePage";
import { ClaimDetailPage } from "./features/claims/ClaimDetailPage";
import { MyClaimsPage } from "./features/claims/MyClaimsPage";
import { CustomerDraftPage } from "./features/claims/CustomerDraftPage";
import { AdminConfigPage } from "./features/admin/AdminConfigPage";
import { CustomerAccountsPage } from "./features/admin/CustomerAccountsPage";
import { statusTone } from "./features/claims/statusPresentation";
import type { ClaimStatus } from "./features/claims/types";

const claimStatusChartColor: Record<ClaimStatus, string> = {
  DRAFT: "#64748b",
  SUBMITTED: "#0f766e",
  ANALYZING: "#2563eb",
  REVIEW_REQUIRED: "#d97706",
  AI_APPROVED: "#059669",
  AI_REJECTED: "#dc2626",
  FAILED: "#dc2626",
};

function DashboardPage() {
  const { data, error, isPending } = useDashboardOverview();
  const { session } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const reviewQueue =
    data?.claims.filter(
      (claim) =>
        claim.status === "SUBMITTED" || claim.status === "REVIEW_REQUIRED",
    ) ?? [];
  const chartData =
    data?.queueMix.map((point) => ({
      name: t(`claim.status.${point.status}`),
      status: point.status,
      value: point.value,
    })) ?? [];
  const canCreateClaim = session?.user.role === "ADMIN";

  return (
    <div className="page-layout mx-auto grid max-w-[1440px] gap-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="mb-2 text-sm font-semibold text-slate-500">
            {t("dashboard.eyebrow")}
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-950">
            {t("dashboard.title")}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            {t("dashboard.description")}
          </p>
        </div>
        {canCreateClaim ? (
          <Button
            className="w-full sm:w-auto"
            onPress={() => navigate("/claims/new")}
            variant="primary"
          >
            <CloudUpload size={18} />
            {t("dashboard.newClaim")}
          </Button>
        ) : null}
      </header>

      <div className="dashboard-metrics grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Document}
          label={t("dashboard.totalClaims")}
          loading={isPending}
          value={data?.metrics.totalClaims}
        />
        <MetricCard
          icon={WarningAlt}
          label={t("dashboard.pendingReviews")}
          loading={isPending}
          tone="warning"
          value={data?.metrics.pendingReviews}
        />
        <MetricCard
          icon={CheckmarkOutline}
          label={t("dashboard.aiApproved")}
          loading={isPending}
          tone="success"
          value={data?.metrics.aiApproved}
        />
        <MetricCard
          icon={ErrorOutline}
          label={t("dashboard.aiRejected")}
          loading={isPending}
          tone="danger"
          value={data?.metrics.aiRejected}
        />
      </div>

      <div className="dashboard-overview grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card className="rounded-lg border border-slate-200 bg-surface shadow-sm">
          <Card.Header className="border-b border-slate-100 px-5 py-4">
            <Card.Title className="flex items-center gap-2 text-lg text-slate-950">
              <ChartColumn size={20} />
              {t("dashboard.statusOverview")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("dashboard.statusOverviewDescription")}
            </Card.Description>
          </Card.Header>
          <Card.Content className="min-h-80 p-5">
            {isPending ? <Skeleton className="h-full rounded-lg" /> : null}
            {error ? <InlineError message={t("dashboard.loadError")} /> : null}
            {data && chartData.length > 0 ? (
              <ResponsiveContainer height="100%" width="100%">
                <BarChart
                  data={chartData}
                  layout="vertical"
                  margin={{ left: 0, right: 28, top: 4, bottom: 4 }}
                >
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis
                    allowDecimals={false}
                    fontSize={12}
                    stroke="var(--muted)"
                    tickLine={false}
                    type="number"
                  />
                  <YAxis
                    interval={0}
                    axisLine={false}
                    dataKey="name"
                    fontSize={12}
                    stroke="var(--muted)"
                    tickLine={false}
                    type="category"
                    width={132}
                  />
                  <ChartTooltip
                    cursor={{ fill: "var(--surface-secondary)" }}
                    contentStyle={{
                      background: "var(--overlay)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      color: "var(--foreground)",
                    }}
                  />
                  <Bar
                    isAnimationActive={false}
                    barSize={22}
                    dataKey="value"
                    radius={[0, 4, 4, 0]}
                    shape={<ClaimStatusBar />}
                  >
                    <LabelList
                      className="fill-slate-700 text-xs font-semibold"
                      dataKey="value"
                      position="right"
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : null}
            {data && chartData.length === 0 ? (
              <EmptyState>
                <div className="text-sm font-semibold text-slate-950">
                  {t("dashboard.noActivity")}
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  {t("dashboard.noActivityDescription")}
                </p>
              </EmptyState>
            ) : null}
          </Card.Content>
        </Card>

        <aside>
          <Card className="h-full rounded-lg border border-slate-200 bg-surface shadow-sm">
            <Card.Header className="border-b border-slate-100 px-5 py-4">
              <Card.Title className="text-lg text-slate-950">
                {t("dashboard.needsReview")}
              </Card.Title>
              <Card.Description className="text-sm text-slate-500">
                {t("dashboard.needsReviewDescription")}
              </Card.Description>
            </Card.Header>
            <Card.Content className="grid content-start gap-2 p-3">
              {isPending ? <QueueSkeleton /> : null}
              {data && reviewQueue.length
                ? reviewQueue.slice(0, 5).map((claim) => (
                    <Link
                      className="grid gap-1 rounded-lg px-3 py-3 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      key={claim.id}
                      to={`/claims/${claim.id}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold text-blue-700">
                          {claim.id}
                        </span>
                        <Chip
                          color={statusTone[claim.status]}
                          size="sm"
                          variant="soft"
                        >
                          {t(`claim.status.${claim.status}`)}
                        </Chip>
                      </div>
                      <span className="truncate text-sm text-slate-700">
                        {claim.claimant}
                      </span>
                      <span className="text-xs text-slate-500">
                        {claim.vehicle}
                      </span>
                    </Link>
                  ))
                : null}
              {data && reviewQueue.length === 0 ? (
                <p className="px-2 py-8 text-center text-sm text-slate-500">
                  {t("dashboard.noReviewQueue")}
                </p>
              ) : null}
            </Card.Content>
          </Card>
        </aside>
      </div>

      <Card className="rounded-lg border border-slate-200 bg-surface shadow-sm">
        <Card.Header className="border-b border-slate-100 px-5 py-4">
          <Card.Title className="text-lg text-slate-950">
            {t("dashboard.recentClaims")}
          </Card.Title>
          <Card.Description className="text-sm text-slate-500">
            {t("dashboard.recentDescription")}
          </Card.Description>
        </Card.Header>
        <Card.Content className="p-5">
          {isPending ? <QueueSkeleton /> : null}
          {error ? <InlineError message={t("dashboard.loadError")} /> : null}
          {data && data.claims.length > 0 ? (
            <ClaimQueueTable claims={data.claims} />
          ) : null}
          {data && data.claims.length === 0 ? (
            <EmptyState>
              <div className="text-sm font-semibold text-slate-950">
                {t("dashboard.noClaims")}
              </div>
              <p className="mt-1 text-sm text-slate-500">
                {t("dashboard.noClaimsDescription")}
              </p>
            </EmptyState>
          ) : null}
        </Card.Content>
      </Card>
    </div>
  );
}

function ClaimStatusBar({
  height = 0,
  payload,
  width = 0,
  x = 0,
  y = 0,
}: {
  height?: number;
  payload?: { status: ClaimStatus };
  width?: number;
  x?: number;
  y?: number;
}) {
  return (
    <rect
      fill={payload ? claimStatusChartColor[payload.status] : "#2563eb"}
      height={height}
      rx={4}
      ry={4}
      width={width}
      x={x}
      y={y}
    />
  );
}

function ClaimsPage() {
  const { data, error, isPending } = useDashboardOverview();
  const { session } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const canCreateClaim = session?.user.role === "ADMIN";

  return (
    <div className="page-layout mx-auto grid max-w-[1440px] gap-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            {t("claimsList.eyebrow")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {t("claimsList.title")}
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {t("claimsList.description")}
          </p>
        </div>
        {canCreateClaim ? (
          <Button
            className="w-full sm:w-auto"
            onPress={() => navigate("/claims/new")}
            variant="primary"
          >
            <CloudUpload size={18} />
            {t("dashboard.newClaim")}
          </Button>
        ) : null}
      </header>

      <Card className="rounded-lg border border-slate-200 bg-surface shadow-sm">
        <Card.Header className="border-b border-slate-100 px-5 py-4">
          <Card.Title className="text-lg text-slate-950">
            {t("claimsList.allClaims")}
          </Card.Title>
          <Card.Description className="text-sm text-slate-500">
            {t("claimsList.allClaimsDescription")}
          </Card.Description>
        </Card.Header>
        <Card.Content className="p-5">
          {isPending ? <QueueSkeleton /> : null}
          {error ? <InlineError message={t("claimsList.loadError")} /> : null}
          {data && data.claims.length > 0 ? (
            <ClaimQueueTable claims={data.claims} />
          ) : null}
          {data && data.claims.length === 0 ? (
            <EmptyState>
              <div className="text-sm font-semibold text-slate-950">
                {t("dashboard.noClaims")}
              </div>
              <p className="mt-1 text-sm text-slate-500">
                {t("dashboard.noClaimsDescription")}
              </p>
            </EmptyState>
          ) : null}
        </Card.Content>
      </Card>
    </div>
  );
}

function AccessRestricted() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const { t } = useTranslation();

  return (
    <div className="flex min-h-full items-center justify-center px-5">
      <Card className="w-full max-w-lg rounded-lg border border-slate-200 bg-surface shadow-sm">
        <Card.Content className="p-8">
          <h1 className="text-2xl font-semibold text-slate-950">
            {t("access.title")}
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {t("access.description")}
          </p>
          <Button
            className="mt-6"
            onPress={() =>
              navigate(
                session?.user.role === "USER" ? "/my-claims" : "/dashboard",
              )
            }
            variant="primary"
          >
            {session?.user.role === "USER"
              ? t("myClaims.title")
              : t("access.returnToDashboard")}
          </Button>
        </Card.Content>
      </Card>
    </div>
  );
}

export function AppRoutes() {
  return (
    <>
      <Toast.Provider
        className="z-50"
        maxVisibleToasts={3}
        placement="top end"
      />
      <Routes>
        <Route element={<LoginPage />} path="/login" />
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route
            element={
              <RoleRoute
                fallback={<AccessRestricted />}
                role={["ADMIN", "ADJUSTER"]}
              >
                <DashboardPage />
              </RoleRoute>
            }
            path="/dashboard"
          />
          <Route
            element={
              <RoleRoute
                fallback={<AccessRestricted />}
                role={["ADMIN", "ADJUSTER"]}
              >
                <ClaimsPage />
              </RoleRoute>
            }
            path="/claims"
          />
          <Route
            element={
              <RoleRoute
                fallback={<AccessRestricted />}
                role={["ADMIN", "USER"]}
              >
                <ClaimCreatePage />
              </RoleRoute>
            }
            path="/claims/new"
          />
          <Route
            element={
              <RoleRoute
                fallback={<AccessRestricted />}
                role={["ADMIN", "ADJUSTER"]}
              >
                <ClaimDetailPage />
              </RoleRoute>
            }
            path="/claims/:claimId"
          />
          <Route
            element={
              <RoleRoute fallback={<AccessRestricted />} role="USER">
                <MyClaimsPage />
              </RoleRoute>
            }
            path="/my-claims"
          />
          <Route
            element={
              <RoleRoute fallback={<AccessRestricted />} role="USER">
                <CustomerDraftPage />
              </RoleRoute>
            }
            path="/my-claims/:claimId/edit"
          />
          <Route
            element={
              <RoleRoute fallback={<AccessRestricted />} role="ADMIN">
                <AdminConfigPage />
              </RoleRoute>
            }
            path="/admin"
          />
          <Route
            element={
              <RoleRoute fallback={<AccessRestricted />} role="ADMIN">
                <CustomerAccountsPage />
              </RoleRoute>
            }
            path="/customer-accounts"
          />
        </Route>
        <Route element={<DefaultRedirect />} path="*" />
      </Routes>
    </>
  );
}

function DefaultRedirect() {
  const { session } = useAuth();
  return (
    <Navigate
      replace
      to={session?.user.role === "USER" ? "/my-claims" : "/dashboard"}
    />
  );
}

function App() {
  return <AppRoutes />;
}

type MetricCardProps = {
  icon: typeof Document;
  label: string;
  loading: boolean;
  tone?: "default" | "success" | "warning" | "danger";
  value?: number | string;
};

function MetricCard({
  icon: Icon,
  label,
  loading,
  tone = "default",
  value,
}: MetricCardProps) {
  const toneClasses = {
    default: "bg-blue-50 text-blue-700 ring-blue-100",
    success: "bg-emerald-50 text-emerald-700 ring-emerald-100",
    warning: "bg-amber-50 text-amber-700 ring-amber-100",
    danger: "bg-red-50 text-red-700 ring-red-100",
  };

  return (
    <Card
      className={`metric-card metric-card--${tone} rounded-lg border border-slate-200 bg-surface shadow-sm`}
    >
      <Card.Content className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-slate-500">{label}</div>
            {loading ? (
              <Skeleton className="mt-3 h-8 w-24 rounded-lg" />
            ) : (
              <div className="metric-value mt-2 text-3xl font-semibold text-slate-950">
                {value ?? "-"}
              </div>
            )}
          </div>
          <div
            className={`flex size-10 items-center justify-center rounded-lg ring-1 ${toneClasses[tone]}`}
          >
            <Icon size={20} />
          </div>
        </div>
      </Card.Content>
    </Card>
  );
}

function QueueSkeleton() {
  return (
    <div className="grid gap-3">
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-12 rounded-lg" />
    </div>
  );
}

function InlineError({ message }: { message: string }) {
  const { t } = useTranslation();

  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
      <ErrorOutline className="mt-0.5 shrink-0" size={18} />
      <div>
        <div className="text-sm font-semibold">{t("queue.loadFailed")}</div>
        <p className="mt-1 text-sm">{message}</p>
      </div>
    </div>
  );
}

export default App;
