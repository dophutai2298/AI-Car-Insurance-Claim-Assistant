import { useState, type FormEvent } from 'react'
import { Add, ArrowLeft, CarFront } from '@carbon/icons-react'
import { Alert, Button, Card, Input, Label, TextField } from '@heroui/react'
import { Link, useNavigate } from 'react-router'

import { ClaimsApiError } from './claimsApi'
import { useCreateClaim } from './useClaims'

export function ClaimCreatePage() {
  const navigate = useNavigate()
  const createClaim = useCreateClaim()
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
      setError(caughtError instanceof ClaimsApiError ? caughtError.message : 'Unable to create claim')
    }
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
        <Link className="flex w-fit items-center gap-2 text-sm font-semibold text-blue-700" to="/claims">
          <ArrowLeft size={18} />
          Back to claims
        </Link>
        <header>
          <p className="text-sm font-semibold text-slate-500">Claim intake</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Create a claim case</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Start an evidence review case. This does not approve or reject an insurance claim.
          </p>
        </header>

        <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
            <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
              <CarFront size={20} />
            </div>
            <div>
              <Card.Title className="text-lg text-slate-950">Vehicle and claimant</Card.Title>
              <Card.Description className="text-sm text-slate-500">
                Basic case metadata for the upcoming evidence workflow.
              </Card.Description>
            </div>
          </Card.Header>
          <Card.Content className="p-6">
            <form className="grid gap-5" onSubmit={handleSubmit}>
              {error ? (
                <Alert status="danger">
                  <Alert.Title>Unable to create claim</Alert.Title>
                  <Alert.Description>{error}</Alert.Description>
                </Alert>
              ) : null}
              <TextField fullWidth isRequired name="claimant_name">
                <Label>Claimant name</Label>
                <Input onChange={(event) => setClaimantName(event.target.value)} value={claimantName} />
              </TextField>
              <div className="grid gap-5 sm:grid-cols-2">
                <TextField fullWidth isRequired name="make">
                  <Label>Make</Label>
                  <Input onChange={(event) => setMake(event.target.value)} value={make} />
                </TextField>
                <TextField fullWidth isRequired name="model">
                  <Label>Model</Label>
                  <Input onChange={(event) => setModel(event.target.value)} value={model} />
                </TextField>
                <TextField fullWidth isRequired name="year" type="number">
                  <Label>Year</Label>
                  <Input inputMode="numeric" onChange={(event) => setYear(event.target.value)} value={year} />
                </TextField>
                <TextField fullWidth name="license_plate">
                  <Label>License plate</Label>
                  <Input onChange={(event) => setLicensePlate(event.target.value)} value={licensePlate} />
                </TextField>
              </div>
              <TextField fullWidth name="vin">
                <Label>VIN</Label>
                <Input onChange={(event) => setVin(event.target.value)} value={vin} />
              </TextField>
              <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
                <Button onPress={() => navigate('/dashboard')} variant="ghost">
                  Cancel
                </Button>
                <Button isPending={createClaim.isPending} type="submit" variant="primary">
                  <Add size={18} />
                  Create claim
                </Button>
              </div>
            </form>
          </Card.Content>
        </Card>
    </div>
  )
}
