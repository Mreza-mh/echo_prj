import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { GenericHttpService } from '../@shared/services/generic-http.service';

@Injectable({
  providedIn: 'root',
})
export class AuthHTTPService {
  constructor(
    private http: HttpClient,
    private genericHttpService: GenericHttpService,
  ) {}
  checkmoobile(data: { email: string }): Observable<any> {
    return this.genericHttpService.post<any>(`/auth/send/verification`, data);
  }

  loginWithPassword(data: { email: string; password: string }): Observable<any> {
    return this.genericHttpService.post<any>(`/auth/login/password`, data);
  }

  loginWithSms(data: { email: string; verification_code: string }): Observable<any> {
    return this.genericHttpService.post<any>('/auth/login/verification', data);
  }
  resendConfirmCode(data: any): Observable<any> {
    return this.genericHttpService.post<any>(`/auth/resend/confirmcode`, data);
  }
  setPassword(data: any): Observable<any> {
    return this.genericHttpService.put(`/auth/set/password`, data);
  }

  resetPassword(data: any): Observable<any> {
    return this.genericHttpService.post('/auth/forget-password', data);
  }

  loginPassword(data: any): Observable<any> {
    return this.genericHttpService.post<any>(`/auth/login/password`, data);
  }
  verifyToken(): Observable<any> {
    return this.genericHttpService.get(`/auth/get/me`);
  }

  getMe(): Observable<any> {
    return this.genericHttpService.get(`/auth/get/me`);
  }

  editProfile(data: { name: string; birthday: string }): Observable<any> {
    return this.genericHttpService.put(`/auth/edit/profile`, data);
  }

  listUsers(params: {
    name?: string;
    mobile?: string;
    count_item?: number;
    is_paginate?: boolean;
  }): Observable<any> {
    return this.genericHttpService.post<any>(`/auth/list-user`, params);
  }
}
