import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Service,
  CreateServiceRequest,
  UpdateServiceRequest,
  ServiceFilterRequest,
} from '../models/service.model';

@Injectable({
  providedIn: 'root',
})
export class ServiceManagementService {
  private readonly apiUrl = '/service';

  constructor(private http: HttpClient) {}

  getServices(filter?: ServiceFilterRequest): Observable<any> {
    const requestBody = {
      is_paginate: filter?.is_paginate ?? true,
      count_item: filter?.count_item ?? 10,
      title: filter?.title || ''
    };

    return this.http.post<any>(`${this.apiUrl}/list`, requestBody);
  }

  getService(id: number): Observable<Service> {
    return this.http.get<Service>(`${this.apiUrl}/${id}`);
  }

  createService(data: CreateServiceRequest): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/add`, data);
  }

  updateService(id: number, data: Partial<UpdateServiceRequest>): Observable<any> {
    return this.http.patch<any>(`${this.apiUrl}/edit/${id}`, data);
  }

  deleteService(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/delete/${id}`);
  }
}
