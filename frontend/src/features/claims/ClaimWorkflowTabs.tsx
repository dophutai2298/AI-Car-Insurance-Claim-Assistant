import { useEffect, useRef, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  claimSteps,
  type ClaimStepId,
  type ClaimStepState,
} from "./ClaimWorkflowStepper";

const stateColors: Record<ClaimStepState, string> = {
  completed: "border-blue-600 bg-blue-600 text-white",
  current: "border-blue-600 bg-blue-600 text-white",
  available: "border-blue-200 bg-blue-50 text-blue-700",
  blocked: "border-slate-200 bg-slate-100 text-slate-500",
  warning: "border-amber-300 bg-amber-50 text-amber-800",
  error: "border-red-300 bg-red-50 text-red-700",
};

export function ClaimWorkflowTabs({
  selected,
  states,
  onSelect,
}: {
  selected: ClaimStepId;
  states: Partial<Record<ClaimStepId, ClaimStepState>>;
  onSelect: (step: ClaimStepId) => void;
}) {
  const { t } = useTranslation();
  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const viewport = viewportRef.current;
    const activeTab = viewport?.querySelector<HTMLButtonElement>(
      '[role="tab"][aria-selected="true"]',
    );
    if (!viewport || !activeTab) return;

    const viewportBounds = viewport.getBoundingClientRect();
    const tabBounds = activeTab.getBoundingClientRect();
    if (tabBounds.left < viewportBounds.left) {
      viewport.scrollLeft -= viewportBounds.left - tabBounds.left;
    } else if (tabBounds.right > viewportBounds.right) {
      viewport.scrollLeft += tabBounds.right - viewportBounds.right;
    }
  }, [selected]);

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    let nextIndex: number;
    switch (event.key) {
      case "ArrowRight":
        nextIndex = (index + 1) % claimSteps.length;
        break;
      case "ArrowLeft":
        nextIndex = (index - 1 + claimSteps.length) % claimSteps.length;
        break;
      case "Home":
        nextIndex = 0;
        break;
      case "End":
        nextIndex = claimSteps.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    onSelect(claimSteps[nextIndex].id);
    event.currentTarget.parentElement
      ?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
      [nextIndex]?.focus();
  }

  return (
    <div
      className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm"
      ref={viewportRef}
    >
      <div
        aria-label={t("claim.workflow")}
        className="flex min-w-[45rem] border-b border-slate-200"
        role="tablist"
      >
        {claimSteps.map((step, index) => {
          const state = states[step.id] ?? "blocked";
          const isSelected = selected === step.id;
          return (
            <button
              aria-controls={`claim-panel-${step.id}`}
              aria-selected={isSelected}
              className={`flex min-h-20 min-w-0 flex-1 items-center gap-3 border-b-2 px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-blue-600 ${isSelected ? "border-blue-600 bg-blue-50" : "border-transparent hover:bg-slate-50"}`}
              id={`claim-tab-${step.id}`}
              key={step.id}
              onClick={() => onSelect(step.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              role="tab"
              tabIndex={isSelected ? 0 : -1}
              type="button"
            >
              <span
                aria-hidden="true"
                className={`flex size-8 shrink-0 items-center justify-center rounded-md border text-xs font-semibold ${stateColors[state]}`}
              >
                {index + 1}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold leading-5 text-slate-950">
                  {t(step.labelKey)}
                </span>
                <span className="block text-xs text-slate-600">
                  {t(`claim.${state}`)}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
