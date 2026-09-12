import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { vehicleMakesKey } from "../vehicleMakes/useVehicleMakes";
import type {
  VehicleManufacturerUpdate,
  VehicleManufacturerWrite,
} from "../vehicleMakes/types";
import {
  createVehicleManufacturer,
  getAdminVehicleManufacturers,
  updateVehicleManufacturer,
} from "./adminApi";

export const adminVehicleManufacturersKey = ["admin", "vehicle-makes"] as const;

function invalidateVehicleManufacturerQueries(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: adminVehicleManufacturersKey }),
    queryClient.invalidateQueries({ queryKey: vehicleMakesKey }),
  ]);
}

export function useAdminVehicleManufacturers() {
  const { session } = useAuth();
  return useQuery({
    queryKey: adminVehicleManufacturersKey,
    queryFn: () => getAdminVehicleManufacturers(session!.access_token),
    enabled: Boolean(session),
  });
}

export function useCreateVehicleManufacturer() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: VehicleManufacturerWrite) =>
      createVehicleManufacturer(values, session!.access_token),
    onSuccess: () => invalidateVehicleManufacturerQueries(queryClient),
  });
}

export function useUpdateVehicleManufacturer() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      manufacturerId,
      values,
    }: {
      manufacturerId: number;
      values: VehicleManufacturerUpdate;
    }) =>
      updateVehicleManufacturer(manufacturerId, values, session!.access_token),
    onSuccess: () => invalidateVehicleManufacturerQueries(queryClient),
  });
}
