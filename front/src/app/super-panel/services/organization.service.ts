import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { 
  Organization, 
  CreateOrganizationRequest, 
  UpdateOrganizationRequest, 
  OrganizationFilterRequest 
} from '../models/organization.model';

// API Response interface matching the backend specification
interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  private readonly apiUrl = '/organization';

  constructor(private http: HttpClient) {}

  /**
   * Get list of organizations with optional filtering
   * Uses POST method as per API specification
   */
  getOrganizations(filter?: OrganizationFilterRequest): Observable<Organization[]> {
    const requestBody = {
      is_paginate: filter?.is_paginate ?? true,
      count_item: filter?.count_item ?? 10,
      name: filter?.name || filter?.search || '',
      business_type: filter?.business_type || '',
      address: filter?.address || '',
      phone: filter?.phone || ''
    };

    return this.http.post<ApiResponse<any>>(this.apiUrl + '/list', requestBody)
      .pipe(
        map(response => {
          console.log('API Response from /list:', response);
          if (response.success && response.data) {
            // The structure is { success: true, message: "...", data: { current_page: 1, data: [...] } }
            if (response.data.data && Array.isArray(response.data.data)) {
              return response.data.data;
            }
            // Handle cases where data itself is the array
            if (Array.isArray(response.data)) {
              return response.data;
            }
          }
          return [];
        }),
        catchError(error => {
          console.error('Error fetching organizations', error);
          return of([]);
        })
      );
  }

  /**
   * Get organization details by ID
   */
  getOrganization(id: string): Observable<Organization> {
    return this.http.post<ApiResponse<Organization>>(`${this.apiUrl}/${id}`, {})
      .pipe(map(response => response.data));
  }

  /**
   * Create new organization
   */
  createOrganization(data: CreateOrganizationRequest): Observable<Organization> {
    return this.http.post<ApiResponse<Organization>>(`${this.apiUrl}/add`, data)
      .pipe(map(response => response.data));
  }

  /**
   * Update existing organization
   */
  updateOrganization(id: string, data: Partial<UpdateOrganizationRequest>): Observable<Organization> {
    return this.http.patch<ApiResponse<Organization>>(`${this.apiUrl}/edit/${id}`, data)
      .pipe(map(response => response.data));
  }

  /**
   * Delete organization
   */
  deleteOrganization(id: string): Observable<void> {
    return this.http.delete<ApiResponse<void>>(`${this.apiUrl}/delete/${id}`, {})
      .pipe(map(() => void 0));
  }

  /**
   * Add admin to organization
   */
  addAdmin( user_id: number): Observable<any> {
    return this.http.post<ApiResponse<any>>(`${this.apiUrl}/add-admin`, {  user_id });
  }
}