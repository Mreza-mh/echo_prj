import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { GenericHttpService } from '../@shared/services/generic-http.service';
import { AuthHTTPService } from '../auth/auth-http.service';

@Injectable({
  providedIn: 'root',
})
export class DoctorHttpService {
  private genericHttp = inject(GenericHttpService);
  private authHttp = inject(AuthHTTPService);

  getCurrentUser(): Observable<any> {
    return this.authHttp.getMe();
  }

  getCurrentAppointment(params?: { staff_id?: number | null }): Observable<any> {
    const query = params?.staff_id != null ? `?staff_id=${params.staff_id}` : '';
    return this.genericHttp.get(`/appointment/get-current-appointment${query}`);
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

  getCalendarDashboard(data: { start_date: string; end_date?: string; staff_ids?: number[] }): Observable<any> {
    return this.genericHttp.post('/appointment/get-calendar-dashboard', data);
  }

  getAppointments(data: any = {}): Observable<any> {
    return this.genericHttp.post('/appointment/list', data);
  }
}
