import { Add, CheckmarkOutline, Edit, PauseOutline } from "@carbon/icons-react";
import {
  Alert,
  Button,
  Card,
  Chip,
  EmptyState,
  Input,
  Label,
  Skeleton,
  TextField,
} from "@heroui/react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  useAdminVehicleManufacturers,
  useCreateVehicleManufacturer,
  useUpdateVehicleManufacturer,
} from "./useVehicleManufacturers";
import type { VehicleManufacturer } from "../vehicleMakes/types";

export function VehicleManufacturerPanel() {
  const { t } = useTranslation();
  const manufacturers = useAdminVehicleManufacturers();
  const createManufacturer = useCreateVehicleManufacturer();
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await createManufacturer.mutateAsync({ name });
      setName("");
    } catch {
      setError(t("manufacturers.saveError"));
    }
  }

  return (
    <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <Card.Header className="border-b border-slate-100 px-6 py-5">
        <Card.Title className="text-lg text-slate-950">
          {t("manufacturers.title")}
        </Card.Title>
        <Card.Description className="text-sm text-slate-500">
          {t("manufacturers.description")}
        </Card.Description>
      </Card.Header>
      <Card.Content className="grid gap-5 p-6">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={create}
        >
          <TextField
            className="min-w-0 flex-1"
            fullWidth
            isRequired
            name="manufacturer-name"
          >
            <Label>{t("manufacturers.name")}</Label>
            <Input
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
          </TextField>
          <Button
            isPending={createManufacturer.isPending}
            type="submit"
            variant="primary"
          >
            <Add size={18} />
            {t("manufacturers.add")}
          </Button>
        </form>
        {error ? (
          <Alert status="danger">
            <Alert.Title>{t("manufacturers.saveError")}</Alert.Title>
            <Alert.Description>{error}</Alert.Description>
          </Alert>
        ) : null}
        {manufacturers.isPending ? (
          <Skeleton className="h-40 rounded-lg" />
        ) : null}
        {manufacturers.error ? (
          <Alert status="danger">
            <Alert.Title>{t("manufacturers.unavailable")}</Alert.Title>
            <Alert.Description>
              {t("manufacturers.loadError")}
            </Alert.Description>
          </Alert>
        ) : null}
        {manufacturers.data?.length === 0 ? (
          <EmptyState>{t("manufacturers.empty")}</EmptyState>
        ) : null}
        {manufacturers.data?.length ? (
          <div className="overflow-x-auto max-h-[600px] rounded-lg border border-slate-200">
            <table className="w-full min-w-[38rem] border-collapse text-left text-sm">
              <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3" scope="col">
                    {t("manufacturers.name")}
                  </th>
                  <th className="w-28 px-4 py-3" scope="col">
                    {t("manufacturers.status")}
                  </th>
                  <th className="w-56 px-4 py-3" scope="col">
                    {t("manufacturers.actions")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {manufacturers.data.map((manufacturer) => (
                  <ManufacturerRow
                    key={manufacturer.id}
                    manufacturer={manufacturer}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card.Content>
    </Card>
  );
}

function ManufacturerRow({
  manufacturer,
}: {
  manufacturer: VehicleManufacturer;
}) {
  const { t } = useTranslation();
  const updateManufacturer = useUpdateVehicleManufacturer();
  const [name, setName] = useState(manufacturer.name);
  const [error, setError] = useState("");

  async function update(values: { name: string; is_active: boolean }) {
    setError("");
    try {
      await updateManufacturer.mutateAsync({
        manufacturerId: manufacturer.id,
        values,
      });
    } catch {
      setError(t("manufacturers.saveError"));
    }
  }

  return (
    <>
      <tr className="align-middle hover:bg-slate-50">
        <td className="px-4 py-3">
          <TextField fullWidth isRequired name={`manufacturer-${manufacturer.id}`}>
            <Label className="sr-only">{t("manufacturers.name")}</Label>
            <Input
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
          </TextField>
        </td>
        <td className="px-4 py-3">
          <Chip
            color={manufacturer.is_active ? "success" : "default"}
            size="sm"
            variant="soft"
          >
            {manufacturer.is_active
              ? t("manufacturers.active")
              : t("manufacturers.disabled")}
          </Chip>
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <Button
              isPending={updateManufacturer.isPending}
              onPress={() =>
                update({ name, is_active: manufacturer.is_active })
              }
              size="sm"
              variant="secondary"
            >
              <Edit size={16} />
              {t("manufacturers.save")}
            </Button>
            <Button
              isPending={updateManufacturer.isPending}
              onPress={() =>
                update({
                  name: manufacturer.name,
                  is_active: !manufacturer.is_active,
                })
              }
              size="sm"
              variant="ghost"
            >
              {manufacturer.is_active ? (
                <PauseOutline size={16} />
              ) : (
                <CheckmarkOutline size={16} />
              )}
              {manufacturer.is_active
                ? t("manufacturers.disable")
                : t("manufacturers.enable")}
            </Button>
          </div>
        </td>
      </tr>
      {error ? (
        <tr>
          <td className="px-4 pb-3 text-sm text-red-700" colSpan={3}>
            {error}
          </td>
        </tr>
      ) : null}
    </>
  );
}
