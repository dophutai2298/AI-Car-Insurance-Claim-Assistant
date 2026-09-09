import { useState, type FormEvent } from 'react'
import { Add, ArrowLeft, CarFront } from '@carbon/icons-react'
import { Alert, Autocomplete, Button, Card, EmptyState, Input, Label, ListBox, SearchField, TextField, useFilter } from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'

import { ClaimsApiError } from './claimsApi'
import { useCreateClaim } from './useClaims'
import { ClaimWorkflowStepper } from './ClaimWorkflowStepper'
import { useVehicleMakes } from '../vehicleMakes/useVehicleMakes'

export function ClaimCreatePage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { contains } = useFilter({ sensitivity: 'base' })
  const createClaim = useCreateClaim()
  const vehicleMakes = useVehicleMakes()
  const [error, setError] = useState('')
  const [claimantName, setClaimantName] = useState('')
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [year, setYear] = useState('')
  const [licensePlate, setLicensePlate] = useState('')
  const [vin, setVin] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!make) {
      setError(t('claim.selectMakeRequired'))
      return
    }
    try {
      const claim = await createClaim.mutateAsync({
        claimant_name: claimantName,
        vehicle: {
          make,
          model,
          year: Number(year),
          license_plate: licensePlate || null,
          vin: vin || null,
        },
      })
      navigate(`/claims/${claim.id}`)
    } catch (caughtError) {
      setError(caughtError instanceof ClaimsApiError ? caughtError.message : t('claim.unableToCreate'))
    }
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
        <Link className="flex w-fit items-center gap-2 text-sm font-semibold text-blue-700" to="/claims">
          <ArrowLeft size={18} />
          {t('claim.backToClaims')}
        </Link>
        <header>
          <p className="text-sm font-semibold text-slate-500">{t('claim.intake')}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">{t('claim.createTitle')}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {t('claim.createDescription')}
          </p>
        </header>

        <ClaimWorkflowStepper />

        <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
            <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
              <CarFront size={20} />
            </div>
            <div>
              <Card.Title className="text-lg text-slate-950">{t('claim.vehicleAndClaimant')}</Card.Title>
              <Card.Description className="text-sm text-slate-500">
                {t('claim.vehicleDescription')}
              </Card.Description>
            </div>
          </Card.Header>
          <Card.Content className="p-6">
            <form className="grid gap-5" onSubmit={handleSubmit}>
              {error ? (
                <Alert status="danger">
                  <Alert.Title>{t('claim.unableToCreate')}</Alert.Title>
                  <Alert.Description>{error}</Alert.Description>
                </Alert>
              ) : null}
              <TextField fullWidth isRequired name="claimant_name">
                <Label>{t('claim.claimantName')}</Label>
                <Input onChange={(event) => setClaimantName(event.target.value)} value={claimantName} />
              </TextField>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="grid gap-2">
                <Autocomplete fullWidth isRequired name="make" placeholder={t('claim.selectMake')} selectionMode="single" value={make || null} onChange={(key) => setMake(key ? String(key) : '')}>
                  <Label>{t('claim.vehicleMake')}</Label>
                  <Autocomplete.Trigger><Autocomplete.Value /><Autocomplete.Indicator /></Autocomplete.Trigger>
                  <Autocomplete.Popover>
                    <Autocomplete.Filter filter={contains}>
                      <SearchField aria-label={t('claim.searchMakes')} autoFocus name="vehicle-make-search" variant="secondary"><SearchField.Group><SearchField.SearchIcon /><SearchField.Input placeholder={t('claim.searchMakes')} /><SearchField.ClearButton /></SearchField.Group></SearchField>
                      {!vehicleMakes.isPending && !vehicleMakes.isError ? (
                        <ListBox renderEmptyState={() => <EmptyState>{t('claim.noMakes')}</EmptyState>}>
                          {(vehicleMakes.data ?? []).map((manufacturer) => <ListBox.Item id={manufacturer.name} key={manufacturer.id} textValue={manufacturer.name}>{manufacturer.name}<ListBox.ItemIndicator /></ListBox.Item>)}
                        </ListBox>
                      ) : null}
                    </Autocomplete.Filter>
                  </Autocomplete.Popover>
                </Autocomplete>
                {vehicleMakes.isPending ? <p className="text-sm text-slate-500" role="status">{t('claim.loadingMakes')}</p> : null}
                {vehicleMakes.isError ? <p className="text-sm text-red-700" role="alert">{t('claim.unableToLoadMakes')}</p> : null}
                {!vehicleMakes.isPending && !vehicleMakes.isError && (vehicleMakes.data?.length ?? 0) === 0 ? <p className="text-sm text-slate-500">{t('claim.noMakes')}</p> : null}
                </div>
                <TextField fullWidth isRequired name="model">
                  <Label>{t('claim.vehicleModel')}</Label>
                  <Input onChange={(event) => setModel(event.target.value)} value={model} />
                </TextField>
                <TextField fullWidth isRequired name="year" type="number">
                  <Label>{t('claim.vehicleYear')}</Label>
                  <Input inputMode="numeric" onChange={(event) => setYear(event.target.value)} value={year} />
                </TextField>
                <TextField fullWidth name="license_plate">
                  <Label>{t('claim.licensePlate')}</Label>
                  <Input onChange={(event) => setLicensePlate(event.target.value)} value={licensePlate} />
                </TextField>
              </div>
              <TextField fullWidth name="vin">
                <Label>{t('claim.vin')}</Label>
                <Input onChange={(event) => setVin(event.target.value)} value={vin} />
              </TextField>
              <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
                <Button onPress={() => navigate('/dashboard')} variant="ghost">
                  {t('claim.cancel')}
                </Button>
                <Button isPending={createClaim.isPending} type="submit" variant="primary">
                  <Add size={18} />
                  {t('claim.create')}
                </Button>
              </div>
            </form>
          </Card.Content>
        </Card>
    </div>
  )
}
