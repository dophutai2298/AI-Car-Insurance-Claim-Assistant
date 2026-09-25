import {
  Activity,
  CarFront,
  ChartColumn,
  CheckmarkOutline,
  CloudUpload,
  Document,
  ErrorOutline,
  Logout,
  SettingsAdjust,
  WarningAlt,
} from "@carbon/icons-react";
import { Button, Card, Chip, EmptyState, Skeleton } from "@heroui/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Link,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useNavigate,
} from "react-router";
import { useTranslation } from "react-i18next";

import { ClaimQueueTable } from "./features/dashboard/ClaimQueueTable";
import { useDashboardOverview } from "./features/dashboard/useDashboardOverview";
import { LoginPage } from "./features/auth/LoginPage";
import { useAuth } from "./features/auth/AuthProvider";
import { LanguageSwitcher } from "./features/auth/LanguageSwitcher";
import { ProtectedRoute, RoleRoute } from "./features/auth/ProtectedRoute";
import { ClaimCreatePage } from "./features/claims/ClaimCreatePage";
import { ClaimDetailPage } from "./features/claims/ClaimDetailPage";
import { AdminConfigPage } from "./features/admin/AdminConfigPage";
import { statusLabel, statusTone } from "./features/claims/statusPresentation";

function AppShell() {
  const { logout, session } = useAuth();
  const { t } = useTranslation();
  const navigation = [
    { label: t("navigation.dashboard"), icon: Activity, path: "/dashboard" },
    { label: t("navigation.claims"), icon: Document, path: "/claims" },
    {
      label: t("navigation.admin"),
      icon: SettingsAdjust,
      path: "/admin",
      adminOnly: true,
    },
  ];
  const visibleNavigation = navigation.filter(
    (item) => !item.adminOnly || session?.user.role === "ADMIN",
  );

  return (
    <main className="h-dvh overflow-hidden bg-slate-100 text-slate-950">
      <div className="grid h-full grid-cols-1 grid-rows-[auto_minmax(0,1fr)] overflow-hidden lg:grid-cols-[272px_minmax(0,1fr)] lg:grid-rows-1">
        <aside className="shrink-0 overflow-hidden border-b border-slate-200 bg-slate-950 px-5 py-5 text-white lg:h-full lg:border-b-0 lg:border-r lg:border-slate-800">
          <div className="flex h-full flex-col gap-6">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-blue-500 text-white">
                <CarFront size={22} />
              </div>
              <div>
                <div className="text-sm font-semibold">Claim Assistant</div>
                <div className="text-xs text-slate-400">Insurance PoC</div>
              </div>
            </div>

            <nav
              className="grid grid-cols-3 gap-2 lg:grid-cols-1"
              aria-label="Primary navigation"
            >
              {visibleNavigation.map((item) => {
                const Icon = item.icon;

                return (
                  <NavLink
                    className={({ isActive }) =>
                      [
                        "flex min-h-11 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors lg:justify-start",
                        isActive
                          ? "bg-blue-600 text-white shadow-sm"
                          : "text-slate-300 hover:bg-slate-900 hover:text-white",
                      ].join(" ")
                    }
                    key={item.label}
                    to={item.path}
                  >
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>

            <div className="mt-auto border-t border-slate-800 pt-4">
              {/* <LanguageSwitcher /> */}
              <div className="mb-3 mt-4 hidden min-w-0 lg:block">
                <div className="truncate text-sm font-semibold text-white">
                  {session?.user.full_name}
                </div>
                <div className="truncate text-xs text-slate-400">
                  {session?.user.email}
                </div>
              </div>
              <Button
                className="hidden w-full justify-start lg:flex"
                onPress={logout}
                size="sm"
                variant="danger-soft"
              >
                <Logout size={17} />
                {t("navigation.signOut")}
              </Button>
            </div>
          </div>
        </aside>

        <section className="min-h-0 min-w-0 overflow-x-hidden overflow-y-auto px-4 py-4 sm:px-6 lg:px-8">
          <Outlet />
        </section>
      </div>
    </main>
  );
}

function DashboardPage() {
  const { data, error, isPending } = useDashboardOverview();
  const { session } = useAuth();
  const navigate = useNavigate();
  const reviewQueue =
    data?.claims.filter((claim) => claim.status === "REVIEW_REQUIRED") ?? [];
  const chartData =
    data?.queueMix.map((point) => ({
      name: statusLabel[point.status],
      value: point.value,
    })) ?? [];
  const canCreateClaim = session?.user.role === "ADMIN";

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="mb-2 text-sm font-semibold text-slate-500">
            Claims operations
          </p>
          <h1 className="max-w-3xl text-3xl font-semibold text-slate-950 sm:text-4xl">
            Claim review workspace
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Monitor incoming claim files, focus the review queue, and open the
            evidence record that needs attention.
          </p>
        </div>
        {canCreateClaim ? (
          <Button
            className="w-full sm:w-auto"
            onPress={() => navigate("/claims/new")}
            variant="primary"
          >
            <CloudUpload size={18} />
            New claim
          </Button>
        ) : null}
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Document}
          label="Total claims"
          loading={isPending}
          value={data?.metrics.totalClaims}
        />
        <MetricCard
          icon={WarningAlt}
          label="Pending reviews"
          loading={isPending}
          tone="warning"
          value={data?.metrics.pendingReviews}
        />
        <MetricCard
          icon={CheckmarkOutline}
          label="AI review approved"
          loading={isPending}
          tone="success"
          value={data?.metrics.aiApproved}
        />
        <MetricCard
          icon={ErrorOutline}
          label="AI review rejected"
          loading={isPending}
          tone="danger"
          value={data?.metrics.aiRejected}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <Card.Header className="border-b border-slate-100 px-5 py-4">
            <Card.Title className="flex items-center gap-2 text-lg text-slate-950">
              <ChartColumn size={20} />
              Claim status overview
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              Current volume by workflow status. AI outcomes are not final
              insurer decisions.
            </Card.Description>
          </Card.Header>
          <Card.Content className="h-72 p-5">
            {isPending ? <Skeleton className="h-full rounded-lg" /> : null}
            {error ? (
              <InlineError message="Dashboard data could not be loaded." />
            ) : null}
            {data && chartData.length > 0 ? (
              <ResponsiveContainer height="100%" width="100%">
                <BarChart
                  data={chartData}
                  margin={{ left: -20, right: 12, top: 12, bottom: 12 }}
                >
                  <CartesianGrid stroke="#e2e8f0" vertical={false} />
                  <XAxis
                    dataKey="name"
                    fontSize={12}
                    interval={0}
                    stroke="#64748b"
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    fontSize={12}
                    stroke="#64748b"
                    tickLine={false}
                  />
                  <Tooltip cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : null}
            {data && chartData.length === 0 ? (
              <EmptyState>
                <div className="text-sm font-semibold text-slate-950">
                  No claim activity yet
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  Status counts will appear once a claim is created.
                </p>
              </EmptyState>
            ) : null}
          </Card.Content>
        </Card>

        <aside>
          <Card className="h-full rounded-lg border border-slate-200 bg-white shadow-sm">
            <Card.Header className="border-b border-slate-100 px-5 py-4">
              <Card.Title className="text-lg text-slate-950">
                Needs review
              </Card.Title>
              <Card.Description className="text-sm text-slate-500">
                Cases waiting for an adjuster decision.
              </Card.Description>
            </Card.Header>
            <Card.Content className="grid gap-2 p-3">
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
                          {statusLabel[claim.status]}
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
                  No claims currently require adjuster review.
                </p>
              ) : null}
            </Card.Content>
          </Card>
        </aside>
      </div>

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="border-b border-slate-100 px-5 py-4">
          <Card.Title className="text-lg text-slate-950">
            Recent claims
          </Card.Title>
          <Card.Description className="text-sm text-slate-500">
            Latest activity first. Search by case details, then narrow the queue
            by status or update date.
          </Card.Description>
        </Card.Header>
        <Card.Content className="p-5">
          {isPending ? <QueueSkeleton /> : null}
          {error ? (
            <InlineError message="Dashboard data could not be loaded." />
          ) : null}
          {data && data.claims.length > 0 ? (
            <ClaimQueueTable claims={data.claims} />
          ) : null}
          {data && data.claims.length === 0 ? (
            <EmptyState>
              <div className="text-sm font-semibold text-slate-950">
                No claims yet
              </div>
              <p className="mt-1 text-sm text-slate-500">
                Create a claim to begin evidence intake.
              </p>
            </EmptyState>
          ) : null}
        </Card.Content>
      </Card>
    </div>
  );
}

function ClaimsPage() {
  const { data, error, isPending } = useDashboardOverview();
  const { session } = useAuth();
  const navigate = useNavigate();
  const canCreateClaim = session?.user.role === "ADMIN";

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">Claims</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            Claim cases
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Review active intake cases and open their evidence records.
          </p>
        </div>
        {canCreateClaim ? (
          <Button
            className="w-full sm:w-auto"
            onPress={() => navigate("/claims/new")}
            variant="primary"
          >
            <CloudUpload size={18} />
            New claim
          </Button>
        ) : null}
      </header>

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="border-b border-slate-100 px-5 py-4">
          <Card.Title className="text-lg text-slate-950">All claims</Card.Title>
          <Card.Description className="text-sm text-slate-500">
            Current cases ordered by their latest update.
          </Card.Description>
        </Card.Header>
        <Card.Content className="p-5">
          {isPending ? <QueueSkeleton /> : null}
          {error ? (
            <InlineError message="Claim cases could not be loaded." />
          ) : null}
          {data && data.claims.length > 0 ? (
            <ClaimQueueTable claims={data.claims} />
          ) : null}
          {data && data.claims.length === 0 ? (
            <EmptyState>
              <div className="text-sm font-semibold text-slate-950">
                No claims yet
              </div>
              <p className="mt-1 text-sm text-slate-500">
                Create a claim to begin evidence intake.
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

  return (
    <div className="flex min-h-full items-center justify-center px-5">
      <Card className="w-full max-w-lg rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Content className="p-8">
          <h1 className="text-2xl font-semibold text-slate-950">
            Access restricted
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Admin configuration is available only to users with the Admin role.
          </p>
          <Button
            className="mt-6"
            onPress={() => navigate("/dashboard")}
            variant="primary"
          >
            Return to dashboard
          </Button>
        </Card.Content>
      </Card>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<LoginPage />} path="/login" />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route element={<DashboardPage />} path="/dashboard" />
        <Route element={<ClaimsPage />} path="/claims" />
        <Route element={<ClaimCreatePage />} path="/claims/new" />
        <Route element={<ClaimDetailPage />} path="/claims/:claimId" />
        <Route
          element={
            <RoleRoute fallback={<AccessRestricted />} role="ADMIN">
              <AdminConfigPage />
            </RoleRoute>
          }
          path="/admin"
        />
      </Route>
      <Route element={<Navigate replace to="/dashboard" />} path="*" />
    </Routes>
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
    <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <Card.Content className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-slate-500">{label}</div>
            {loading ? (
              <Skeleton className="mt-3 h-8 w-24 rounded-lg" />
            ) : (
              <div className="mt-2 font-mono text-3xl font-semibold text-slate-950">
                {value}
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
  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
      <ErrorOutline className="mt-0.5 shrink-0" size={18} />
      <div>
        <div className="text-sm font-semibold">Unable to load queue</div>
        <p className="mt-1 text-sm">{message}</p>
      </div>
    </div>
  );
}

export default App;
