import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import i18n from '../../i18n'
import { ClaimWorkflowStepper } from './ClaimWorkflowStepper'

test('renders each supported claim workflow state', async () => {
  await i18n.changeLanguage('en')
  render(
    <ClaimWorkflowStepper
      current="humanReview"
      states={{
        information: 'completed',
        evidence: 'available',
        analysis: 'warning',
        aiReview: 'blocked',
        humanReview: 'current',
      }}
    />,
  )

  expect(screen.getByText('Completed')).toBeVisible()
  expect(screen.getByText('Available')).toBeVisible()
  expect(screen.getByText('Warning')).toBeVisible()
  expect(screen.getByText('Blocked')).toBeVisible()
  expect(screen.getByText('Current')).toBeVisible()
})
