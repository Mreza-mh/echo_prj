import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { VitalMonitorService, VitalReading } from './vital-monitor.service';
import { GenericHttpService } from '../../@shared/services/generic-http.service';
import { TranslationService } from '../../@shared/services/translation.service';

@Component({
  selector: 'app-vital-monitor',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatButtonModule, MatIconModule, MatCardModule,
    MatProgressSpinnerModule, MatSnackBarModule,
  ],
  templateUrl: './vital-monitor.component.html',
  styleUrls: ['./vital-monitor.component.scss'],
})
export class VitalMonitorComponent implements OnInit, OnDestroy {
  private vitalService = inject(VitalMonitorService);
  private http         = inject(GenericHttpService);
  private snack        = inject(MatSnackBar);
  private translationService = inject(TranslationService);

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  // مدت session: سنسور فیزیکی هر ~۲ ثانیه یک خوانده تولید می‌کند (کد ESP32 ثابت است)،
  // پس ۱۲۰ ثانیه ≈ ۶۰ نقطه برای نمودار — روند قابل‌قبول. دکمه «توقف دستی» همیشه در دسترس است.
  readonly SESSION_SECS = 120;

  searchQuery     = '';
  patients: any[] = [];
  selectedPatient: any = null;

  private searchSubject = new Subject<string>();
  private searchSub?:    Subscription;

  measuring  = false;
  loading    = false;
  readings: VitalReading[] = [];
  countdown  = 0;

  private liveSub?:      Subscription;
  private countdownRef?: ReturnType<typeof setInterval>;

  // آخرین خوانده معتبر (نه صرفاً آخرین)
  get latestValidHr(): number {
    return [...this.readings].reverse().find(r => r.valid_hr && r.heart_rate > 0)?.heart_rate ?? 0;
  }
  get hasValidHr():   boolean { return this.latestValidHr > 0; }
  get countdownPct(): number  { return (this.countdown / this.SESSION_SECS) * 100; }

  // جدیدترین ابتدا
  get sortedReadings(): VitalReading[] {
    return [...this.readings].reverse();
  }

  formatTime(ts: string): string {
    return new Date(parseInt(ts)).toLocaleTimeString('fa-IR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  }

  // ── نمودار خطی SVG ────────────────────────────────────────
  // ابعاد viewBox — با CSS کشیده می‌شود (preserveAspectRatio="none")
  readonly CHART_W = 620;
  readonly CHART_H = 150;
  readonly CHART_PAD = 14;

  /** مسیر منحنی نرم (Catmull-Rom → Bezier) بین نقاط واقعی — فقط جلوه بصری، نقاط اصلی دست‌نخورده می‌مانند */
  private smoothPath(dots: { x: number; y: number }[]): string {
    if (dots.length === 0) return '';
    if (dots.length === 1) return `M ${dots[0].x.toFixed(1)},${dots[0].y.toFixed(1)}`;
    if (dots.length === 2) {
      return `M ${dots[0].x.toFixed(1)},${dots[0].y.toFixed(1)} L ${dots[1].x.toFixed(1)},${dots[1].y.toFixed(1)}`;
    }

    let d = `M ${dots[0].x.toFixed(1)},${dots[0].y.toFixed(1)}`;
    for (let i = 0; i < dots.length - 1; i++) {
      const p0 = dots[i - 1] ?? dots[i];
      const p1 = dots[i];
      const p2 = dots[i + 1];
      const p3 = dots[i + 2] ?? p2;
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      d += ` C ${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }

  /** تبدیل نقاط (ایندکس، مقدار) به مختصات SVG + مسیر منحنی نرم و ناحیه گرادیان */
  private chartGeometry(
    points: { i: number; v: number }[],
    total: number,
    yMin: number,
    yMax: number,
  ) {
    const W = this.CHART_W, H = this.CHART_H, P = this.CHART_PAD;
    const xOf = (i: number) => total <= 1 ? W / 2 : P + (i * (W - 2 * P)) / (total - 1);
    const yOf = (v: number) => {
      const clamped = Math.min(Math.max(v, yMin), yMax);
      return H - P - ((clamped - yMin) / (yMax - yMin)) * (H - 2 * P);
    };

    const dots = points.map(p => ({ x: xOf(p.i), y: yOf(p.v), v: p.v }));
    const linePath = this.smoothPath(dots);
    const areaPath = dots.length
      ? `${linePath} L ${dots[dots.length - 1].x.toFixed(1)},${H - P} L ${dots[0].x.toFixed(1)},${H - P} Z`
      : '';

    return { dots, linePath, areaPath };
  }

  /** نمودار ضربان قلب — بازه Y داینامیک حول داده‌ها */
  get hrChart() {
    const pts = this.readings
      .map((r, i) => ({ i, v: r.heart_rate, ok: r.valid_hr && r.heart_rate > 0 }))
      .filter(p => p.ok);
    if (pts.length < 2) return null;

    const vals = pts.map(p => p.v);
    let yMin = Math.min(...vals) - 8;
    let yMax = Math.max(...vals) + 8;
    if (yMax - yMin < 20) {           // حداقل بازه ۲۰ تا نوسان کوچک هم دیده شود
      const mid = (yMin + yMax) / 2;
      yMin = mid - 10;
      yMax = mid + 10;
    }
    return { ...this.chartGeometry(pts, this.readings.length, yMin, yMax),
             yMin: Math.round(yMin), yMax: Math.round(yMax) };
  }

  /** آمار session برای نمایش زیر هر نمودار */
  private statsOf(vals: number[]) {
    if (!vals.length) return null;
    const sum = vals.reduce((a, b) => a + b, 0);
    return {
      min: Math.min(...vals),
      max: Math.max(...vals),
      avg: Math.round(sum / vals.length),
    };
  }

  get hrStats() { return this.statsOf(this.readings.filter(r => r.valid_hr && r.heart_rate > 0).map(r => r.heart_rate)); }

  // ── جستجوی بیمار ──────────────────────────────────────────
  ngOnInit(): void {
    this.searchSub = this.searchSubject.pipe(
      debounceTime(400),
      distinctUntilChanged(),
    ).subscribe(query => this._doSearch(query));
  }

  onSearchInput(): void {
    const q = this.searchQuery.trim();
    if (!q) { this.patients = []; return; }
    this.searchSubject.next(q);
  }

  private _doSearch(query: string): void {
    if (query.length < 2) { this.patients = []; return; }
    const isId = /^\d+$/.test(query);
    const params = isId ? { id: parseInt(query, 10) } : { name: query };
    this.http.post('/auth/list-user', params).subscribe({
      next: (res: any) => { this.patients = res?.data?.data ?? res?.data ?? []; },
      error: () => { this.patients = []; },
    });
  }

  selectPatient(p: any): void {
    this.selectedPatient = p;
    this.searchQuery     = '';
    this.patients        = [];
  }

  clearPatient(): void {
    this.selectedPatient = null;
    this.searchQuery     = '';
    this.patients        = [];
  }

  // ── اندازه‌گیری ───────────────────────────────────────────
  startMeasuring(): void {
    if (!this.selectedPatient) return;
    this.loading = true;

    this.vitalService.startSession(this.selectedPatient.id).subscribe({
      next: (res: any) => {
        this.measuring = true;
        this.loading   = false;
        this.readings  = [];
        this.countdown = this.SESSION_SECS;

        // زمان شروع session از ساعت «سرور» — تا فقط داده‌های همین session نمایش داده شود
        const sinceMs = parseInt(res?.data?.started_at) || Date.now();

        this.liveSub = this.vitalService.liveData$(this.selectedPatient.id, sinceMs).subscribe({
          next: (r: any) => { this.readings = r?.data ?? []; },
        });

        // countdown + auto-stop
        this.countdownRef = setInterval(() => {
          this.countdown--;
          if (this.countdown <= 0) {
            clearInterval(this.countdownRef);
            this._doStop();
            this.snack.open(`اندازه‌گیری ${this.SESSION_SECS} ثانیه‌ای تکمیل شد`, '', { duration: 3000 });
          }
        }, 1000);

        this.snack.open('اندازه‌گیری شروع شد', '', { duration: 2000 });
      },
      error: () => { this.loading = false; },
    });
  }

  stopMeasuring(): void {
    clearInterval(this.countdownRef);
    this._doStop();
    this.snack.open('اندازه‌گیری متوقف شد', '', { duration: 2000 });
  }

  private _doStop(): void {
    this.vitalService.stopSession().subscribe();
    this.liveSub?.unsubscribe();
    this.measuring = false;
    this.countdown = 0;
  }

  saveToProfile(): void {
    if (!this.selectedPatient) return;
    this.vitalService.saveToProfile(this.selectedPatient.id).subscribe({
      next: (res: any) => {
        const d = res?.data;
        this.snack.open(
          `ذخیره شد — ضربان: ${d?.avg_hr} bpm`,
          'OK',
          { duration: 4000 },
        );
      },
    });
  }

  ngOnDestroy(): void {
    clearInterval(this.countdownRef);
    this.liveSub?.unsubscribe();
    this.searchSub?.unsubscribe();
    if (this.measuring) this.vitalService.stopSession().subscribe();
  }
}
