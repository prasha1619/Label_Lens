/**
 * Maps backend product_category IDs to the user-facing display labels.
 * These must match the five categories defined in the spec:
 *   Food and Beverage | Electronics and Electrical |
 *   General Packaged Commodities | Pharmaceuticals | Cosmetics and Toiletries
 */
export const CATEGORY_LABELS: Record<string, string> = {
  food_and_beverages:         'Food and Beverage',
  electronics_and_appliances: 'Electronics and Electrical',
  packaged_commodity:         'General Packaged Commodities',
  pharmaceuticals:            'Pharmaceuticals',
  cosmetics_and_toiletries:   'Cosmetics and Toiletries',
};

/**
 * Returns the human-readable label for a category ID.
 * Falls back to a title-cased version of the ID if the ID is unknown.
 */
export function getCategoryLabel(categoryId: string): string {
  return (
    CATEGORY_LABELS[categoryId] ??
    categoryId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  );
}
