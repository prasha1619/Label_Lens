import { request, API_BASE } from './api';
import { DemoSample, InspectionResponse } from '../types/inspection';

export const demoService = {
  async getDemoSamples(): Promise<DemoSample[]> {
    return request<DemoSample[]>('/demo/samples');
  },

  async runDemoInspection(sampleKey: string): Promise<InspectionResponse> {
    return request<InspectionResponse>(`/demo/run/${sampleKey}`, {
      method: 'POST',
    });
  },

  getDemoSampleImageUrl(sampleKey: string): string {
    return `${API_BASE}/demo/samples/${sampleKey}/image`;
  }
};
