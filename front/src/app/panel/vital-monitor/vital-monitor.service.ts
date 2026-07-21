import { Injectable, inject } from '@angular/core';
import { Observable, interval, switchMap, startWith, share } from 'rxjs';
import { GenericHttpService } from '../../@shared/services/generic-http.service';

export interface VitalReading {
  heart_rate: number;
  valid_hr: boolean;
  recorded_at: string;
}

@Injectable({ providedIn: 'root' })
export class VitalMonitorService {
  private http = inject(GenericHttpService);

  private DEVICE_ID = 'ESP32_001';

  private readonly POLL_MS = 2000; // هر 2 ثانیه یه درخواست جدید میده
  // توی esp PUBLISH_INTERVAL_MS=2000  sync
  //  published esp, get front every 2s

  startSession(patientId: number): Observable<any> {
    return this.http.post('/vitals/start', {
      patient_id: patientId,
      device_id: this.DEVICE_ID,
    });
  }
  // {
  //     "device_id":"ESP32_001",
  //     "patient_id":15,
  //     "started_at":"1753045678000"
  // }
  stopSession(): Observable<any> {
    return this.http.post('/vitals/stop', { device_id: this.DEVICE_ID });
  }
  // sinceMs = session start time
  liveData$(patientId: number, sinceMs?: number): Observable<any> {
    const since = sinceMs ? `?since=${sinceMs}` : '';
    return interval(this.POLL_MS).pipe(
      startWith(0), // first req
      switchMap(() => this.http.get(`/vitals/live/${patientId}${since}`)),
      // share(),
    );
  }

  saveToProfile(patientId: number): Observable<any> {
    return this.http.patch(`/vitals/save/${patientId}`, {});
  }
}
