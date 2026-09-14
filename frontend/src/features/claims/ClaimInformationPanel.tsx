import { CarFront, Edit, Save } from "@carbon/icons-react";
import {
  Alert,
  Autocomplete,
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  ListBox,
  SearchField,
  TextField,
  useFilter,
} from "@heroui/react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useVehicleMakes } from "../vehicleMakes/useVehicleMakes";
import { ClaimsApiError } from "./claimsApi";
import type { ClaimDetail } from "./types";
import { useUpdateClaimInformation } from "./useClaims";

export function ClaimInformationPanel({ claim }: { claim: ClaimDetail }) {
  const { t } = useTranslation();
  const { contains } = useFilter({ sensitivity: "base" });
  const vehicleMakes = useVehicleMakes();
  const update = useUpdateClaimInformation(claim.id);
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState(() => formValues(claim));

  useEffect(() => setValues(formValues(claim)), [claim]);
  const locked =
    claim.status === "ANALYZING" ||
    claim.status === "AI_APPROVED" ||
    claim.status === "AI_REJECTED";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await update.mutateAsync({
      claimant_name: values.claimantName,
      vehicle: {
        make: values.make,
        model: values.model,
        year: Number(values.year),
        license_plate: values.licensePlate || null,
        vin: values.vin || null,
      },
      incident: {
        occurred_at: new Date(values.incidentAt).toISOString(),
        location: values.location,
        description: values.description,
      },
    });
    setEditing(false);
  }

  return (
    <Card
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
      id="information"
    >
      <Card.Header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
            <CarFront size={20} />
          </div>
          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("claim.information")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("claim.informationDescription")}
            </Card.Description>
          </div>
        </div>
        {!editing ? (
          <Button
            isDisabled={locked}
            onPress={() => setEditing(true)}
            variant="outline"
          >
            <Edit size={17} />
            {t("common.edit")}
          </Button>
        ) : null}
      </Card.Header>
      <Card.Content className="p-6">
        {editing ? (
          <form className="grid gap-5" onSubmit={submit}>
            {update.error ? (
              <Alert status="danger">
                <Alert.Title>{t("claim.updateFailed")}</Alert.Title>
                <Alert.Description>
                  {update.error instanceof ClaimsApiError
                    ? update.error.message
                    : t("common.tryAgain")}
                </Alert.Description>
              </Alert>
            ) : null}
            <TextField isRequired>
              <Label>{t("claim.claimantName")}</Label>
              <Input
                value={values.claimantName}
                onChange={(event) =>
                  setValues({ ...values, claimantName: event.target.value })
                }
              />
            </TextField>
            <div className="grid gap-5 md:grid-cols-2">
              <Autocomplete
                isRequired
                placeholder={t("claim.selectMake")}
                selectionMode="single"
                value={values.make || null}
                onChange={(key) =>
                  setValues({ ...values, make: key ? String(key) : "" })
                }
              >
                <Label>{t("claim.vehicleMake")}</Label>
                <Autocomplete.Trigger>
                  <Autocomplete.Value />
                  <Autocomplete.Indicator />
                </Autocomplete.Trigger>
                <Autocomplete.Popover>
                  <Autocomplete.Filter filter={contains}>
                    <SearchField
                      aria-label={t("claim.searchMakes")}
                      autoFocus
                      variant="secondary"
                    >
                      <SearchField.Group>
                        <SearchField.SearchIcon />
                        <SearchField.Input
                          placeholder={t("claim.searchMakes")}
                        />
                        <SearchField.ClearButton />
                      </SearchField.Group>
                    </SearchField>
                    <ListBox
                      renderEmptyState={() => (
                        <EmptyState>{t("claim.noMakes")}</EmptyState>
                      )}
                    >
                      {(vehicleMakes.data ?? []).map((item) => (
                        <ListBox.Item id={item.name} key={item.id}>
                          {item.name}
                          <ListBox.ItemIndicator />
                        </ListBox.Item>
                      ))}
                    </ListBox>
                  </Autocomplete.Filter>
                </Autocomplete.Popover>
              </Autocomplete>
              <TextField isRequired>
                <Label>{t("claim.vehicleModel")}</Label>
                <Input
                  value={values.model}
                  onChange={(event) =>
                    setValues({ ...values, model: event.target.value })
                  }
                />
              </TextField>
              <TextField isRequired type="number">
                <Label>{t("claim.vehicleYear")}</Label>
                <Input
                  value={values.year}
                  onChange={(event) =>
                    setValues({ ...values, year: event.target.value })
                  }
                />
              </TextField>
              <TextField>
                <Label>{t("claim.licensePlate")}</Label>
                <Input
                  value={values.licensePlate}
                  onChange={(event) =>
                    setValues({ ...values, licensePlate: event.target.value })
                  }
                />
              </TextField>
              <TextField>
                <Label>{t("claim.vin")}</Label>
                <Input
                  value={values.vin}
                  onChange={(event) =>
                    setValues({ ...values, vin: event.target.value })
                  }
                />
              </TextField>
              <TextField isRequired type="datetime-local">
                <Label>{t("claim.incidentAt")}</Label>
                <Input
                  value={values.incidentAt}
                  onChange={(event) =>
                    setValues({ ...values, incidentAt: event.target.value })
                  }
                />
              </TextField>
              <TextField isRequired>
                <Label>{t("claim.incidentLocation")}</Label>
                <Input
                  value={values.location}
                  onChange={(event) =>
                    setValues({ ...values, location: event.target.value })
                  }
                />
              </TextField>
            </div>
            <TextField isRequired>
              <Label>{t("claim.incidentDetails")}</Label>
              <Input
                value={values.description}
                onChange={(event) =>
                  setValues({ ...values, description: event.target.value })
                }
              />
            </TextField>
            <div className="flex justify-end gap-3">
              <Button
                onPress={() => {
                  setValues(formValues(claim));
                  setEditing(false);
                }}
                variant="ghost"
              >
                {t("claim.cancel")}
              </Button>
              <Button
                isPending={update.isPending}
                type="submit"
                variant="primary"
              >
                <Save size={17} />
                {t("common.save")}
              </Button>
            </div>
          </form>
        ) : (
          <dl className="grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
            <Field
              label={t("claim.claimantName")}
              value={claim.claimant_name}
            />
            <Field
              label={t("claim.vehicleMake")}
              value={`${claim.vehicle.make} ${claim.vehicle.model}`}
            />
            <Field
              label={t("claim.vehicleYear")}
              value={String(claim.vehicle.year)}
            />
            <Field
              label={t("claim.licensePlate")}
              value={claim.vehicle.license_plate ?? t("common.notProvided")}
            />
            <Field
              label={t("claim.vin")}
              value={claim.vehicle.vin ?? t("common.notProvided")}
            />
            <Field
              label={t("claim.incidentAt")}
              value={
                claim.incident
                  ? new Date(claim.incident.occurred_at).toLocaleString()
                  : t("common.notProvided")
              }
            />
            <Field
              label={t("claim.incidentLocation")}
              value={claim.incident?.location ?? t("common.notProvided")}
            />
            <div className="sm:col-span-2">
              <Field
                label={t("claim.incidentDetails")}
                value={claim.incident?.description ?? t("common.notProvided")}
              />
            </div>
          </dl>
        )}
      </Card.Content>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium text-slate-950">{value}</dd>
    </div>
  );
}

function formValues(claim: ClaimDetail) {
  const incidentAt = claim.incident
    ? new Date(claim.incident.occurred_at)
    : null;
  return {
    claimantName: claim.claimant_name,
    make: claim.vehicle.make,
    model: claim.vehicle.model,
    year: String(claim.vehicle.year),
    licensePlate: claim.vehicle.license_plate ?? "",
    vin: claim.vehicle.vin ?? "",
    incidentAt: incidentAt
      ? new Date(incidentAt.getTime() - incidentAt.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16)
      : "",
    location: claim.incident?.location ?? "",
    description: claim.incident?.description ?? "",
  };
}
