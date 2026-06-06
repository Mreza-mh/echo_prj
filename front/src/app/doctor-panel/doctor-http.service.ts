import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { GenericHttpService } from '../@shared/services/generic-http.service';
import { environment } from '../../environments/environment';
import { AuthHTTPService } from '../auth/auth-http.service';

@Injectable({
  providedIn: 'root',
})
export class DoctorHttpService {
  private genericHttp = inject(GenericHttpService);
  private http = inject(HttpClient);
  private authHttp = inject(AuthHTTPService);

  getCurrentUser(): Observable<any> {
    return this.authHttp.getMe();
  }

  getCurrentAppointment(params?: any): Observable<any> {
    return this.genericHttp.get('/appointment/get-current-appointment', params);
  }

  getAppointmentDetails(id: string | number): Observable<any> {
    return this.genericHttp.get(`/appointment/get-appointment/${id}`);
  }

  getEchoHistory(): Observable<any> {
    return this.genericHttp.get('/echo-history/info');
  }

  getEchoHistoryByPatient(patientId: string | number): Observable<any> {
    return this.genericHttp.get(`/echo-history/info-doctor/${patientId}`);
  }

  getEchoFile(address: string): Observable<any> {
    const token = sessionStorage.getItem('credentials') || localStorage.getItem('credentials');
    let headers: any = {};
    if (token) {
      const parsed = JSON.parse(token);
      headers = {
        headers: new HttpHeaders({
          Authorization: `Bearer ${parsed?.token}`,
        }),
        responseType: 'blob' as const,
      };
    }
    return this.http.get(environment.apiUrl + `/echo-history/file/${address}`, headers);
  }

  getCalendarDashboard(data: { date: string; user_ids?: number[]; resource_ids?: number[] }): Observable<any> {
    return this.genericHttp.post('/appointment/get-calendar-dashboard', data);
  }

  getAppointments(data: any = {}): Observable<any> {
    return this.genericHttp.post('/appointment/list', data);
  }
}
