import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable} from 'rxjs';
import { environment } from '../../../environments/environment';
@Injectable({
  providedIn: 'root',
})
export class GenericHttpService {
  constructor(private httpClient: HttpClient) {}
  appRoot = environment.apiUrl;
  
get<T>(url: string, options?: any): Observable<Object> {
     const config = options || {};
     config.headers = config.headers || new HttpHeaders({ 'Content-Type': 'application/json' });
     return this.httpClient.get(this.appRoot + url, config);
   }

  delete(url: string, body?: any): Observable<any> {
    const httpOptions = {
      headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
      body: body,
    };
    return this.httpClient.delete(this.appRoot + url, httpOptions);
  }
  post<T>(url: string, data: any, headers?: any): Observable<Object> {
    if (headers == null) {
      headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    }
    if (headers == 'undefined') {
      return this.httpClient.post(this.appRoot + url, data);
    } else {
      return this.httpClient.post(this.appRoot + url, data, { headers });
    }
  }

  put<T>(url: string, body: any = null, headers?: any): Observable<Object> {
    if (headers == null) {
      headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    }
    if (headers == 'undefined') {
      return this.httpClient.put(this.appRoot + url, body);
    } else {
      return this.httpClient.put(this.appRoot + url, body, { headers });
    }
  }
  patch<T>(url: string, body: any = null, headers?: any): Observable<Object> {
    if (headers == null) {
      headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    }
    if (headers == 'undefined') {
      return this.httpClient.patch(this.appRoot + url, body);
    } else {
      return this.httpClient.patch(this.appRoot + url, body, { headers });
    }
  }
}
