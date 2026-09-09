import { Translate } from '@carbon/icons-react'
import { Button } from '@heroui/react'
import { useTranslation } from 'react-i18next'

import { languageStorageKey } from '../../i18n'

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const nextLanguage = i18n.language.startsWith('vi') ? 'en' : 'vi'
  const label = nextLanguage === 'vi' ? t('language.switchToVietnamese') : t('language.switchToEnglish')

  async function changeLanguage() {
    await i18n.changeLanguage(nextLanguage)
    window.localStorage.setItem(languageStorageKey, nextLanguage)
  }

  return <Button className="w-full justify-start" onPress={changeLanguage} size="sm" variant="ghost"><Translate size={17} />{label}</Button>
}
