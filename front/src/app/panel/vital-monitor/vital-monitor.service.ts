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

  // دستگاه هر ۲ ثانیه یک reading منتشر می‌کند — poll با همین بازه سینک است
  // تا درخواست‌های اضافی (بدون داده‌ی جدید) زده نشود
  private readonly POLL_MS = 2000;

  startSession(patientId: number): Observable<any> {
    return this.http.post('/vitals/start', {
      patient_id: patientId,
      device_id: this.DEVICE_ID,
    });
  }

  stopSession(): Observable<any> {
    return this.http.post('/vitals/stop', { device_id: this.DEVICE_ID });
  }

  /**
   * sinceMs: زمان شروع session (میلی‌ثانیه، از پاسخ /vitals/start) — فقط خوانده‌های همین session برمی‌گردد
   */
  liveData$(patientId: number, sinceMs?: number): Observable<any> {
    const since = sinceMs ? `?since=${sinceMs}` : '';
    return interval(this.POLL_MS).pipe(
      startWith(0),
      switchMap(() => this.http.get(`/vitals/live/${patientId}${since}`)),
      share()
    );
  }

  saveToProfile(patientId: number): Observable<any> {
    return this.http.patch(`/vitals/save/${patientId}`, {});
  }
}
