import { Injectable } from '@angular/core';
import { GenericHttpService } from '../@shared/services/generic-http.service';
import { Observable } from 'rxjs';
import { HttpClient, HttpRequest } from '@angular/common/http';

@Injectable({
  providedIn: 'root',
})
export class IndexHttpService {
  constructor(private genericHttpService: GenericHttpService, private http: HttpClient) {}

  getAvailableSlots(data: {
    service_id: string;
    staff_id: string;
    date: string;
  }): Observable<any> {
    return this.genericHttpService.post('/appointment/get-available-slots', data);
  }

  addAppointment(data: any): Observable<any> {
    return this.genericHttpService.post('/appointment/add-appointment', data);
  }

  editAppointment(id: string | number, data: any): Observable<any> {
    return this.genericHttpService.patch(`/appointment/edit-appointment/${id}`, data);
  }

  getAppointmentDetails(id: string | number): Observable<any> {
    return this.genericHttpService.get(`/appointment/get-appointment/${id}`);
  }

  getOrganizationServices(data: any): Observable<any> {
    return this.genericHttpService.post('/service/list', data);
  }

  getOrganizationServiceDetails(organ_service_id: string | number): Observable<any> {
    return this.genericHttpService.get(`/service/${organ_service_id}`);
  }

  getStaffList(data: any): Observable<any> {
    return this.genericHttpService.post('/staff/list', data);
  }

  getStaffDetails(staff_id: string | number): Observable<any> {
    return this.genericHttpService.get(`/staff/${staff_id}`);
  }

  getResourceList(data: any): Observable<any> {
    return this.genericHttpService.post('/resource/list', data);
  }

  getResourceDetails(resource_id: string | number): Observable<any> {
    return this.genericHttpService.get(`/resource/${resource_id}`);
  }

  aiChat(messages: any[]): Observable<any> {
    return this.genericHttpService.post('/ai/chat', { messages });
  }

  // User dashboard APIs
  getUserEchoHistory(): Observable<any> {
    return this.genericHttpService.get('/echo-history/info');
  }

  getUserAppointments(data: any = {}): Observable<any> {
    return this.genericHttpService.post('/appointment/list', data);
  }

  // Patient Report APIs (LLM Reports)
  getPatientVisits(patientId: string): Observable<any> {
    return this.genericHttpService.get(`/patient-report/visits/${patientId}`);
  }

  getPatientReport(patientId: string, visitDate: string): Observable<any> {
    return this.genericHttpService.get(`/patient-report/report/${patientId}/${visitDate}`);
  }

  getPatientReportText(patientId: string, visitDate: string): Observable<any> {
    return this.genericHttpService.get(`/patient-report/text/${patientId}/${visitDate}`);
  }

  getPatientSummary(patientId: string): Observable<any> {
    return this.genericHttpService.get(`/patient-report/summary/${patientId}`);
  }

  getPatientReportHtmlUrl(patientId: string, visitDate: string): string {
    // Return the URL for opening in browser/iframe
    return `${this.genericHttpService.getBaseUrl()}/patient-report/html/${patientId}/${visitDate}`;
  }
}
