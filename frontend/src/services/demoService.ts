import { request } from './api';
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
    return `/api/v1/demo/samples/${sampleKey}/image`;
  }
};
