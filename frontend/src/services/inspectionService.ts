import { request, API_BASE } from './api';
import { 
  InspectionResponse, 
  InspectionListResponse, 
  DashboardMetrics 
} from '../types/inspection';

export interface UploadFilePayload {
  file: File;
  panelType?: string;
}

export const inspectionService = {
  async uploadAndAnalyze(
    filesOrPayloads: File | File[] | UploadFilePayload[],
    productCategory: string = 'packaged_commodity',
    explicitPanelTypes?: string[]
  ): Promise<InspectionResponse> {
    const formData = new FormData();
    formData.append('product_category', productCategory);
    formData.append('is_demo', 'false');

    const panelTypes: string[] = [];

    if (Array.isArray(filesOrPayloads)) {
      filesOrPayloads.forEach((item, idx) => {
        if ('file' in item) {
          formData.append('files', item.file);
          panelTypes.push(explicitPanelTypes?.[idx] || item.panelType || 'general');
        } else {
          formData.append('files', item);
          panelTypes.push(explicitPanelTypes?.[idx] || 'general');
        }
      });
    } else {
      formData.append('files', filesOrPayloads);
      panelTypes.push(explicitPanelTypes?.[0] || 'front');
    }

    if (panelTypes.length > 0) {
      formData.append('panel_types', JSON.stringify(panelTypes));
    }

    return request<InspectionResponse>('/inspections', {
      method: 'POST',
      body: formData,
    });
  },


  async getInspection(id: string): Promise<InspectionResponse> {
    return request<InspectionResponse>(`/inspections/${id}`);
  },

  async listInspections(params: {
    page?: number;
    limit?: number;
    category?: string;
    statusFilter?: string;
    search?: string;
  } = {}): Promise<InspectionListResponse> {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page.toString());
    if (params.limit) query.append('limit', params.limit.toString());
    if (params.category) query.append('category', params.category);
    if (params.statusFilter) query.append('status_filter', params.statusFilter);
    if (params.search) query.append('search', params.search);

    return request<InspectionListResponse>(`/inspections?${query.toString()}`);
  },

  async getDashboardMetrics(): Promise<DashboardMetrics> {
    return request<DashboardMetrics>('/inspections/dashboard/metrics');
  },

  async deleteInspection(id: string): Promise<void> {
    await request<void>(`/inspections/${id}`, {
      method: 'DELETE',
    });
  },

  async overrideField(
    id: string,
    fieldName: string,
    value: string,
    unit?: string,
    note?: string
  ): Promise<InspectionResponse> {
    return request<InspectionResponse>(`/inspections/${id}/override-field`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ field_name: fieldName, value, unit, note }),
    });
  },

  async submitReview(
    id: string,
    fieldName: string,
    confirmedValue: string,
    action: string = 'CONFIRM_VALUE',
    sourcePanel?: string,
    reviewerName?: string,
    note?: string
  ): Promise<InspectionResponse> {
    return request<InspectionResponse>(`/inspections/${id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        field_name: fieldName,
        action,
        confirmed_value: confirmedValue,
        source_panel: sourcePanel,
        reviewer_name: reviewerName || 'Statutory Inspector',
        note: note || 'Human verification decision recorded'
      }),
    });
  },

  async uploadMultiPackageScan(
    file: File,
    productCategory: string = 'packaged_commodity'
  ): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('product_category', productCategory);
    formData.append('is_demo', 'false');

    return request<any>('/inspections/multi-package-scan', {
      method: 'POST',
      body: formData,
    });
  },

  async getScanPackages(scanId: string): Promise<InspectionResponse[]> {
    return request<InspectionResponse[]>(`/inspections/scan/${scanId}/packages`);
  },

  async getEvidence(id: string): Promise<any> {
    return request<any>(`/inspections/${id}/evidence`);
  },

  getReportDownloadUrl(id: string): string {
    return `${API_BASE}/inspections/${id}/report`;
  },

  getImageUrl(id: string, annotated: boolean = true, imageIndex: number = 0, imageId?: string): string {
    const params = new URLSearchParams();
    params.append('annotated', annotated.toString());
    params.append('image_index', imageIndex.toString());
    if (imageId) params.append('image_id', imageId);
    return `${API_BASE}/inspections/${id}/image?${params.toString()}`;
  }
};


