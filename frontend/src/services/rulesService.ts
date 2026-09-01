import { request } from './api';
import { ProductCategory, CategorySummary } from '../types/rules';

export const rulesService = {
  async getCategories(): Promise<CategorySummary[]> {
    return request<CategorySummary[]>('/rules');
  },

  async getCategoryRules(categoryId: string): Promise<ProductCategory> {
    return request<ProductCategory>(`/rules/${categoryId}`);
  }
};
