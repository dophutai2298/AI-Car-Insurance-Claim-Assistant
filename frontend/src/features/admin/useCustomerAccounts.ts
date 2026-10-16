import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { getCustomerAccounts } from "./adminApi";

export const customerAccountsKey = ["admin", "customer-accounts"] as const;

export function useCustomerAccounts() {
  const { session } = useAuth();

  return useQuery({
    queryKey: customerAccountsKey,
    queryFn: () => getCustomerAccounts(session!.access_token),
    enabled: Boolean(session),
  });
}

export function useRefreshCustomerAccounts() {
  const queryClient = useQueryClient();

  return () => queryClient.invalidateQueries({ queryKey: customerAccountsKey });
}
