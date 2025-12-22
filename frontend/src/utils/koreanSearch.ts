/**
 * Korean consonant (초성) search utility
 * Enables searching Korean text by typing just the initial consonants.
 * Example: "ㄴ" matches "나레이터", "ㄴㄹㅇㅌ" matches "나레이터"
 */

// Initial consonants (초성) in Unicode order
const CHOSUNG = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
  'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
];

// Unicode range for Korean syllables
const HANGUL_START = 0xAC00; // 가
const HANGUL_END = 0xD7A3;   // 힣
// Each syllable block = (medial vowel count) * (final consonant count) = 21 * 28 = 588
const SYLLABLE_BLOCK = 588;

/**
 * Check if a character is a Korean syllable (가-힣)
 */
function isKoreanSyllable(char: string): boolean {
  const code = char.charCodeAt(0);
  return code >= HANGUL_START && code <= HANGUL_END;
}

/**
 * Check if a character is a Korean initial consonant (ㄱ-ㅎ)
 */
function isChosung(char: string): boolean {
  return CHOSUNG.includes(char);
}

/**
 * Extract the initial consonant (초성) from a Korean syllable
 * Returns the original character if not a Korean syllable
 */
function getChosung(char: string): string {
  if (!isKoreanSyllable(char)) {
    return char;
  }
  const code = char.charCodeAt(0);
  const chosungIndex = Math.floor((code - HANGUL_START) / SYLLABLE_BLOCK);
  return CHOSUNG[chosungIndex];
}

/**
 * Extract all initial consonants from a string
 * Non-Korean characters are preserved as-is
 */
function extractChosung(text: string): string {
  return [...text].map(getChosung).join('');
}

/**
 * Check if the search query consists only of Korean consonants
 */
function isChosungOnly(query: string): boolean {
  if (query.length === 0) return false;
  return [...query].every(char => isChosung(char));
}

/**
 * Search text with Korean consonant (초성) support
 * - If query is all consonants (ㄱ-ㅎ), matches against extracted consonants
 * - Otherwise, performs case-insensitive substring match
 *
 * @param text - The target text to search in
 * @param query - The search query
 * @returns true if the text matches the query
 */
export function koreanSearch(text: string, query: string): boolean {
  if (!query) return true;

  const normalizedQuery = query.trim();
  if (!normalizedQuery) return true;

  // Standard case-insensitive search
  const lowerText = text.toLowerCase();
  const lowerQuery = normalizedQuery.toLowerCase();

  if (lowerText.includes(lowerQuery)) {
    return true;
  }

  // Korean consonant search
  if (isChosungOnly(normalizedQuery)) {
    const textChosung = extractChosung(text);
    return textChosung.includes(normalizedQuery);
  }

  return false;
}

/**
 * Filter an array by Korean-aware search
 * @param items - Array of items to filter
 * @param query - Search query
 * @param getText - Function to extract searchable text from each item
 */
export function filterByKoreanSearch<T>(
  items: T[],
  query: string,
  getText: (item: T) => string
): T[] {
  if (!query.trim()) return items;
  return items.filter(item => koreanSearch(getText(item), query));
}
