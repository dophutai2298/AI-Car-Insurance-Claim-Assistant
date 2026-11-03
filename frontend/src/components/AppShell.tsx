import {
  Activity,
  ArrowUp,
  ChevronRight,
  Close,
  CloudUpload,
  Document,
  Logout,
  Menu,
  SettingsAdjust,
  User,
} from "@carbon/icons-react";
import { Button, Modal, Tooltip } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../features/auth/AuthProvider";
import { LanguageSwitcher } from "../features/auth/LanguageSwitcher";
import { Brand } from "./Brand";
import { ThemeToggle } from "./ThemeToggle";

export function AppShell() {
  const { logout, session } = useAuth();
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const scrollRef = useRef<HTMLElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const role = session?.user.role;
  const navigation =
    role === "USER"
      ? [
          { label: t("myClaims.title"), icon: Document, path: "/my-claims" },
          {
            label: t("myClaims.newClaim"),
            icon: CloudUpload,
            path: "/claims/new",
          },
        ]
      : [
          {
            label: t("navigation.dashboard"),
            icon: Activity,
            path: "/dashboard",
          },
          { label: t("navigation.claims"), icon: Document, path: "/claims" },
          ...(role === "ADMIN"
            ? [
                {
                  label: t("navigation.customerAccounts"),
                  icon: User,
                  path: "/customer-accounts",
                },
                {
                  label: t("navigation.admin"),
                  icon: SettingsAdjust,
                  path: "/admin",
                },
              ]
            : []),
        ];
  const currentPage =
    [...navigation]
      .sort((a, b) => b.path.length - a.path.length)
      .find((item) => pathname.startsWith(item.path))?.label ??
    t("claim.workflow");

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    const onScroll = () => setShowBackToTop(element.scrollTop > 320);
    element.addEventListener("scroll", onScroll, { passive: true });
    return () => element.removeEventListener("scroll", onScroll);
  }, []);

  const sidebar = (
    <div className="sidebar-content">
      <Brand />
      <div className="sidebar-section-label">{t("chrome.workspace")}</div>
      <nav aria-label={t("navigation.primary")} className="sidebar-nav">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "is-active" : ""}`
              }
              onClick={() => setMenuOpen(false)}
            >
              <Icon size={20} aria-hidden="true" />
              <span>{item.label}</span>
              <ChevronRight
                size={14}
                className="sidebar-link__arrow"
                aria-hidden="true"
              />
            </NavLink>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <LanguageSwitcher />
        <div className="sidebar-profile">
          <span className="profile-avatar" aria-hidden="true">
            <User size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold">
              {session?.user.full_name}
            </div>
            <div className="sidebar-profile__role">
              {t(`chrome.roles.${role}`)}
            </div>
          </div>
        </div>
        <Button
          className="sidebar-signout"
          onPress={logout}
          variant="ghost"
          size="sm"
        >
          <Logout size={18} />
          {t("navigation.signOut")}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace-content">
        {t("chrome.skipToContent")}
      </a>
      <aside className="app-sidebar">{sidebar}</aside>
      <div className="workspace">
        <header className="workspace-bar">
          <Modal isOpen={menuOpen} onOpenChange={setMenuOpen}>
            <Button
              className="sidebar-menu-button"
              aria-label={t("chrome.openNavigation")}
              variant="ghost"
              isIconOnly
            >
              <Menu size={22} />
            </Button>
            <Modal.Backdrop>
              <Modal.Container className="navigation-container">
                <Modal.Dialog className="navigation-dialog">
                  <Modal.Heading className="sr-only">
                    {t("navigation.primary")}
                  </Modal.Heading>
                  <Button
                    className="navigation-close"
                    aria-label={t("chrome.closeNavigation")}
                    onPress={() => setMenuOpen(false)}
                    isIconOnly
                    variant="ghost"
                    size="sm"
                  >
                    <Close size={20} />
                  </Button>
                  {sidebar}
                </Modal.Dialog>
              </Modal.Container>
            </Modal.Backdrop>
          </Modal>
          <div className="workspace-breadcrumb">
            <span>{t("chrome.workspace")}</span>
            <ChevronRight size={14} aria-hidden="true" />
            <strong>{currentPage}</strong>
          </div>
          <ThemeToggle />
        </header>
        <main
          id="workspace-content"
          className="workspace-content"
          ref={scrollRef}
          tabIndex={-1}
        >
          <Outlet />
        </main>
      </div>

      {showBackToTop ? (
        <Tooltip>
          <Button
            className="back-to-top"
            aria-label={t("common.backToTop")}
            isIconOnly
            onPress={() =>
              scrollRef.current?.scrollTo({
                top: 0,
                behavior: window.matchMedia?.(
                  "(prefers-reduced-motion: reduce)",
                ).matches
                  ? "instant"
                  : "smooth",
              })
            }
          >
            <ArrowUp size={20} />
          </Button>
          <Tooltip.Content>{t("common.backToTop")}</Tooltip.Content>
        </Tooltip>
      ) : null}
    </div>
  );
}
