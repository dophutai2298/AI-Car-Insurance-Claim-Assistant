import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import {
  getAssessmentRuleHistory,
  getAssessmentRules,
  updateAssessmentRules,
} from "./adminApi";
import type { AssessmentRuleValues } from "./types";

const assessmentRulesKey = ["assessment-rules"] as const;

export function useAssessmentRules() {
  const { session } = useAuth();
  return useQuery({
    queryKey: assessmentRulesKey,
    queryFn: () => getAssessmentRules(session!.access_token),
    enabled: Boolean(session),
  });
}

export function useAssessmentRuleHistory() {
  const { session } = useAuth();
  return useQuery({
    queryKey: [...assessmentRulesKey, "history"],
    queryFn: () => getAssessmentRuleHistory(session!.access_token),
    enabled: Boolean(session),
  });
}

export function useUpdateAssessmentRules() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: AssessmentRuleValues) =>
      updateAssessmentRules(values, session!.access_token),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: assessmentRulesKey });
    },
  });
}
