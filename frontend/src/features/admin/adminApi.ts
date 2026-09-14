import type {
  AssessmentRuleChange,
  AssessmentRuleConfiguration,
  AssessmentRuleValues,
} from "./types";
import type {
  VehicleManufacturer,
  VehicleManufacturerUpdate,
  VehicleManufacturerWrite,
} from "../vehicleMakes/types";

export class AdminApiError extends Error {}

async function request<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  const body: unknown = await response.json();
  if (!response.ok) {
    const message =
      validationMessage(body) ?? "Unable to complete administrator request";
    throw new AdminApiError(message);
  }
  return body as T;
}

function validationMessage(body: unknown) {
  if (typeof body !== "object" || body === null || !("detail" in body))
    return null;
  if (typeof body.detail === "string") return body.detail;
  if (!Array.isArray(body.detail)) return null;
  const messages = body.detail
    .map((detail) =>
      typeof detail === "object" &&
      detail !== null &&
      "msg" in detail &&
      typeof detail.msg === "string"
        ? detail.msg.replace(/^Value error, /, "")
        : null,
    )
    .filter((message): message is string => Boolean(message));
  return messages.length ? messages.join(" ") : null;
}

export function getAssessmentRules(accessToken: string) {
  return request<AssessmentRuleConfiguration>(
    "/api/admin/assessment-rules",
    accessToken,
  );
}

export function updateAssessmentRules(
  values: AssessmentRuleValues,
  accessToken: string,
) {
  return request<AssessmentRuleConfiguration>(
    "/api/admin/assessment-rules",
    accessToken,
    {
      method: "PUT",
      body: JSON.stringify(values),
    },
  );
}

export function getAssessmentRuleHistory(accessToken: string) {
  return request<AssessmentRuleChange[]>(
    "/api/admin/assessment-rules/history",
    accessToken,
  );
}

export function getAdminVehicleManufacturers(accessToken: string) {
  return request<VehicleManufacturer[]>(
    "/api/admin/vehicle-makes",
    accessToken,
  );
}

export function createVehicleManufacturer(
  values: VehicleManufacturerWrite,
  accessToken: string,
) {
  return request<VehicleManufacturer>("/api/admin/vehicle-makes", accessToken, {
    method: "POST",
    body: JSON.stringify(values),
  });
}

export function updateVehicleManufacturer(
  manufacturerId: number,
  values: VehicleManufacturerUpdate,
  accessToken: string,
) {
  return request<VehicleManufacturer>(
    `/api/admin/vehicle-makes/${manufacturerId}`,
    accessToken,
    {
      method: "PUT",
      body: JSON.stringify(values),
    },
  );
}
