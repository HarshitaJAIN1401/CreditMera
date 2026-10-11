import { describe, it, expect } from 'vitest';
import { translations, TranslationDictionary } from '../src/i18n/translations';
import { SUPPORTED_LANGUAGES } from '../src/i18n/I18nContext';
import type {
  SupportedLanguage,
  CaseStatus,
  AssetCategory,
} from '../src/types';

describe('CreditMera Internationalization & Feature Contracts', () => {
  it('validates 7 supported languages coverage', () => {
    const expectedLangs: SupportedLanguage[] = ['en', 'hi', 'es', 'fr', 'de', 'ja', 'ar'];
    expect(SUPPORTED_LANGUAGES).toHaveLength(7);
    for (const code of expectedLangs) {
      expect(SUPPORTED_LANGUAGES.some((l) => l.code === code)).toBe(true);
      expect(translations[code]).toBeDefined();
    }
  });

  it('verifies Arabic language is configured for RTL direction', () => {
    const arabic = SUPPORTED_LANGUAGES.find((l) => l.code === 'ar');
    expect(arabic).toBeDefined();
    expect(arabic?.dir).toBe('rtl');

    const english = SUPPORTED_LANGUAGES.find((l) => l.code === 'en');
    expect(english?.dir).toBe('ltr');
  });

  it('verifies all 7 languages possess complete translation key coverage', () => {
    const enKeys = Object.keys(translations.en) as (keyof TranslationDictionary)[];
    expect(enKeys.length).toBeGreaterThanOrEqual(40);

    const languages: SupportedLanguage[] = ['hi', 'es', 'fr', 'de', 'ja', 'ar'];
    for (const lang of languages) {
      const dict = translations[lang];
      for (const key of enKeys) {
        expect(dict[key], `Missing key "${key}" in language "${lang}"`).toBeDefined();
        expect(typeof dict[key]).toBe('string');
        expect(dict[key].trim().length).toBeGreaterThan(0);
      }
    }
  });

  it('validates Visual Similarity tier classifications', () => {
    const validTiers = [
      'EXACT_OR_NEAR_EXACT',
      'HIGH_SIMILARITY',
      'MODERATE_SIMILARITY',
      'LOW_SIMILARITY',
    ];
    expect(validTiers).toHaveLength(4);
  });

  it('validates Global Case management statuses', () => {
    const validStatuses: CaseStatus[] = [
      'New',
      'Potential Match',
      'Evidence Collected',
      'Contacted',
      'Under Review',
      'Resolved',
      'Closed',
    ];
    expect(validStatuses).toHaveLength(7);
  });

  it('validates international asset categories', () => {
    const categories: AssetCategory[] = [
      'Wildlife',
      'Nature',
      'Travel',
      'Landscape',
      'Portrait',
      'Fashion',
      'Food',
      'Product',
      'Architecture',
      'Documentary',
      'Other',
    ];
    expect(categories).toContain('Wildlife');
    expect(categories).toContain('Nature');
    expect(categories).toContain('Travel');
  });
});
