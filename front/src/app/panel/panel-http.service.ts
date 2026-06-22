import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { GenericHttpService } from '../@shared/services/generic-http.service';
import { PanelService } from './panel.service';

@Injectable({
  providedIn: 'root',
})
export class PanelHttpService {
  private genericHttp = inject(GenericHttpService);
  private panelService = inject(PanelService);

  private get orgId() {
    return this.panelService.getActiveOrganizationId();
  }

  private request<T>(method: string, url: string, data: any = {}): Observable<any> {
    const payload = { ...data };

    switch (method.toLowerCase()) {
      case 'get':
        return this.genericHttp.get(url + (url.includes('?') ? '&' : '?'));
      case 'post':
        return this.genericHttp.post(url, payload);
      case 'patch':
        return this.genericHttp.patch(url, payload);
      case 'delete':
        return this.genericHttp.delete(url, payload);
      default:
        throw new Error(`Method ${method} not supported`);
    }
  }

  // Staff APIs
  getStaffList(data: any = {}): Observable<any> {
    return this.request('post', '/staff/list', data);
  }
  getStaffDetails(id: string): Observable<any> {
    return this.request('get', `/staff/${id}`);
  }
  addStaff(data: any): Observable<any> {
    return this.request('post', '/staff/add', data);
  }
  editStaff(id: string, data: any): Observable<any> {
    return this.request('patch', `/staff/edit/${id}`, data);
  }
  deleteStaff(id: string): Observable<any> {
    return this.request('delete', `/staff/delete/${id}`);
  }

  // Staff Schedule APIs
  getScheduleList(data: any = {}): Observable<any> {
    return this.request('post', '/staff-schedule/list', data);
  }
  getScheduleDetails(id: string): Observable<any> {
    return this.request('get', `/staff-schedule/${id}`);
  }
  addSchedule(user_id : any , data: any): Observable<any> {
    return this.request('post', `/staff-schedule/add/${user_id}`, data);
  }
  editSchedule(id: string, data: any): Observable<any> {
    return this.request('patch', `/staff-schedule/edit/${id}`, data);
  }
  deleteSchedule(id: string): Observable<any> {
    return this.request('delete', `/staff-schedule/delete/${id}`);
  }

  getStatusList(data: any = {}): Observable<any> {
    return this.request('post', '/status/list', data);
  }
  getStatusDetails(id: string): Observable<any> {
    return this.request('get', `/status/${id}`);
  }
  addStatus(data: any): Observable<any> {
    return this.request('post', '/status/add', data);
  }
  editStatus(id: string, data: any): Observable<any> {
    return this.request('patch', `/status/edit/${id}`, data);
  }
  deleteStatus(id: string): Observable<any> {
    return this.request('delete', `/status/delete/${id}`);
  }

  getOrgServiceList(data: any = {}): Observable<any> {
    return this.request('post', '/service/list', data);
  }

  getOrgServiceDetails(id: string): Observable<any> {
    return this.request('get', `/service/${id}`);
  }

  addOrgService(data: any): Observable<any> {
    return this.request('post', '/service/add', data);
  }

  editOrgService(id: string, data: any): Observable<any> {
    return this.request('patch', `/service/edit/${id}`, data);
  }
  deleteOrgService(id: string): Observable<any> {
    return this.request('delete', `/service/delete/${id}`);
  }

  // General Service APIs
  getServiceList(data: any = {}): Observable<any> {
    return this.genericHttp.post('/service/list', data);
  }

  // Resource APIs
  getResourceList(data: any = {}): Observable<any> {
    return this.request('post', '/resource/list', data);
  }
  getResourceDetails(id: string): Observable<any> {
    return this.request('get', `/resource/${id}`);
  }
  addResource(data: any): Observable<any> {
    return this.request('post', '/resource/add', data);
  }
  editResource(id: string, data: any): Observable<any> {
    return this.request('patch', `/resource/edit/${id}`, data);
  }
  deleteResource(id: string): Observable<any> {
    return this.request('delete', `/resource/delete/${id}`);
  }

  // Expertise APIs
  getExpertiseList(data: any = {}): Observable<any> {
    return this.request('post', '/expertise/list', data);
  }
  getExpertiseDetails(id: string): Observable<any> {
    return this.request('get', `/expertise/${id}`);
  }
  addExpertise(data: any): Observable<any> {
    return this.request('post', '/expertise/add', data);
  }
  editExpertise(id: string, data: any): Observable<any> {
    return this.request('patch', `/expertise/edit/${id}`, data);
  }
  deleteExpertise(id: string): Observable<any> {
    return this.request('delete', `/expertise/delete/${id}`);
  }

  // Organization APIs
  getOrganizationDetails(id: string): Observable<any> {
    return this.genericHttp.get(`/organization/${id}`);
  }

  // Appointment & Dashboard APIs
  getCalendarDashboard(data: {
    date?: string;
    start_date?: string;
    end_date?: string;
    staff_ids?: number[];
    resource_ids?: number[];
  }): Observable<any> {
    return this.request('post', '/appointment/get-calendar-dashboard', data);
  }

  getAppointmentDetails(id: string | number): Observable<any> {
    return this.request('get', `/appointment/get-appointment/${id}`);
  }

  editAppointment(id: string | number, data: any): Observable<any> {
    return this.request('patch', `/appointment/edit-appointment/${id}`, data);
  }

  // AI Chat API
  aiChat(messages: any[]): Observable<any> {
    return this.request('post', '/ai/chat', { messages });
  }
}
