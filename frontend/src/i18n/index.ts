import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const languageStorageKey = 'app.language'
const initialLanguage = typeof window !== 'undefined' ? window.localStorage.getItem(languageStorageKey) : null

void i18n.use(initReactI18next).init({
  resources: {
    en: {
      translation: {
        navigation: { dashboard: 'Dashboard', claims: 'Claims', admin: 'Admin Config', signOut: 'Sign out' },
        language: { switchToVietnamese: 'Ti\u1ebfng Vi\u1ec7t', switchToEnglish: 'English' },
        claim: {
          intake: 'Claim intake', createTitle: 'Create a claim case', createDescription: 'Start an evidence review case. This does not approve or reject an insurance claim.',
          information: 'Claim information', workflow: 'Claim workflow', current: 'Current', available: 'Available', blocked: 'Blocked', completed: 'Completed', warning: 'Warning',
          stepEvidence: 'Evidence & documents', stepAnalysis: 'Analysis', stepAiReview: 'AI review', stepHumanReview: 'Human review',
          vehicleAndClaimant: 'Vehicle and claimant', vehicleDescription: 'Basic case metadata for the upcoming evidence workflow.',
          claimantName: 'Claimant name', vehicleMake: 'Vehicle make', vehicleModel: 'Vehicle model', vehicleYear: 'Year', licensePlate: 'License plate', vin: 'VIN',
          searchMakes: 'Search vehicle manufacturers', selectMake: 'Select a vehicle make', selectMakeRequired: 'Select a vehicle make before creating the claim.', loadingMakes: 'Loading vehicle manufacturers...', noMakes: 'No vehicle manufacturers are available.',
          unableToLoadMakes: 'Vehicle manufacturers could not be loaded.', unableToCreate: 'Unable to create claim', cancel: 'Cancel', create: 'Create claim', backToClaims: 'Back to claims',
        },
        manufacturers: {
          title: 'Vehicle manufacturers', description: 'Manage vehicle manufacturers available for new claim intake.', name: 'Manufacturer name', active: 'Active', disabled: 'Disabled',
          add: 'Add manufacturer', save: 'Save manufacturer', enable: 'Enable', disable: 'Disable', empty: 'No vehicle manufacturers found.', unavailable: 'Vehicle manufacturers unavailable.',
          loadError: 'Vehicle manufacturers could not be loaded.', saveError: 'Vehicle manufacturer could not be saved.',
        },
      },
    },
    vi: {
      translation: {
        navigation: { dashboard: 'T\u1ed5ng quan', claims: 'H\u1ed3 s\u01a1', admin: 'C\u1ea5u h\u00ecnh qu\u1ea3n tr\u1ecb', signOut: '\u0110\u0103ng xu\u1ea5t' },
        language: { switchToVietnamese: 'Ti\u1ebfng Vi\u1ec7t', switchToEnglish: 'English' },
        claim: {
          intake: 'Ti\u1ebfp nh\u1eadn y\u00eau c\u1ea7u', createTitle: 'T\u1ea1o h\u1ed3 s\u01a1 y\u00eau c\u1ea7u b\u1ed3i th\u01b0\u1eddng', createDescription: 'Kh\u1edfi t\u1ea1o h\u1ed3 s\u01a1 \u0111\u1ec3 r\u00e0 so\u00e1t ch\u1ee9ng c\u1ee9. Thao t\u00e1c n\u00e0y kh\u00f4ng ph\u00ea duy\u1ec7t ho\u1eb7c t\u1eeb ch\u1ed1i y\u00eau c\u1ea7u b\u1ea3o hi\u1ec3m.',
          information: 'Th\u00f4ng tin y\u00eau c\u1ea7u b\u1ed3i th\u01b0\u1eddng', workflow: 'Quy tr\u00ecnh h\u1ed3 s\u01a1', current: 'Hi\u1ec7n t\u1ea1i', available: 'C\u00f3 th\u1ec3 th\u1ef1c hi\u1ec7n', blocked: 'Ch\u01b0a kh\u1ea3 d\u1ee5ng', completed: 'Ho\u00e0n t\u1ea5t', warning: 'C\u1ea7n l\u01b0u \u00fd',
          stepEvidence: 'Ch\u1ee9ng c\u1ee9 v\u00e0 t\u00e0i li\u1ec7u', stepAnalysis: 'Ph\u00e2n t\u00edch', stepAiReview: 'R\u00e0 so\u00e1t AI', stepHumanReview: 'R\u00e0 so\u00e1t th\u1ee7 c\u00f4ng',
          vehicleAndClaimant: 'Xe v\u00e0 ng\u01b0\u1eddi y\u00eau c\u1ea7u', vehicleDescription: 'Th\u00f4ng tin c\u01a1 b\u1ea3n cho quy tr\u00ecnh ch\u1ee9ng c\u1ee9 ti\u1ebfp theo.',
          claimantName: 'T\u00ean ng\u01b0\u1eddi y\u00eau c\u1ea7u', vehicleMake: 'H\u00e3ng xe', vehicleModel: 'M\u1eabu xe', vehicleYear: 'N\u0103m s\u1ea3n xu\u1ea5t', licensePlate: 'Bi\u1ec3n s\u1ed1 xe', vin: 'S\u1ed1 VIN',
          searchMakes: 'T\u00ecm h\u00e3ng xe', selectMake: 'Ch\u1ecdn h\u00e3ng xe', selectMakeRequired: 'Ch\u1ecdn h\u00e3ng xe tr\u01b0\u1edbc khi t\u1ea1o h\u1ed3 s\u01a1.', loadingMakes: '\u0110ang t\u1ea3i h\u00e3ng xe...', noMakes: 'Kh\u00f4ng c\u00f3 h\u00e3ng xe kh\u1ea3 d\u1ee5ng.',
          unableToLoadMakes: 'Kh\u00f4ng th\u1ec3 t\u1ea3i danh m\u1ee5c h\u00e3ng xe.', unableToCreate: 'Kh\u00f4ng th\u1ec3 t\u1ea1o h\u1ed3 s\u01a1', cancel: 'H\u1ee7y', create: 'T\u1ea1o h\u1ed3 s\u01a1', backToClaims: 'Quay l\u1ea1i h\u1ed3 s\u01a1',
        },
        manufacturers: {
          title: 'H\u00e3ng xe', description: 'Qu\u1ea3n l\u00fd c\u00e1c h\u00e3ng xe kh\u1ea3 d\u1ee5ng khi t\u1ea1o h\u1ed3 s\u01a1 m\u1edbi.', name: 'T\u00ean h\u00e3ng xe', active: '\u0110ang ho\u1ea1t \u0111\u1ed9ng', disabled: '\u0110\u00e3 t\u1eaft',
          add: 'Th\u00eam h\u00e3ng xe', save: 'L\u01b0u h\u00e3ng xe', enable: 'B\u1eadt', disable: 'T\u1eaft', empty: 'Ch\u01b0a c\u00f3 h\u00e3ng xe.', unavailable: 'Kh\u00f4ng th\u1ec3 t\u1ea3i danh m\u1ee5c h\u00e3ng xe.',
          loadError: 'Kh\u00f4ng th\u1ec3 t\u1ea3i danh m\u1ee5c h\u00e3ng xe.', saveError: 'Kh\u00f4ng th\u1ec3 l\u01b0u h\u00e3ng xe.',
        },
      },
    },
  },
  lng: initialLanguage === 'vi' || initialLanguage === 'en' ? initialLanguage : 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export { languageStorageKey }
export default i18n
