import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { MatSelectModule } from '@angular/material/select';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { DoctorHttpService } from '../doctor-http.service';
import { IndexHttpService } from '../../index/index-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
// دیالوگ گالری‌دار داشبورد کاربر (پیمایش بین چند تصویر) — نه نسخه تک‌تصویری قدیمی
import {
  ImageViewerDialogComponent,
  ImageViewerData,
} from '../../index/user-dashboard/image-viewer-dialog.component';
import {
  HeartVisualizationComponent,
  PatientEchoData,
} from '../../index/heart-visualization/heart-visualization';

@Component({
  selector: 'app-echo-history',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
    MatSelectModule,
    MatDialogModule,
    HeartVisualizationComponent,
  ],
  templateUrl: './echo-history.component.html',
  // استایل‌های داشبورد کاربر عیناً بازاستفاده می‌شوند (کارت‌ها، گالری، جدول اندازه‌گیری، گزارش LLM)
  styleUrls: [
    '../../index/user-dashboard/user-dashboard.component.scss',
    './echo-history.component.scss',
  ],
})
export class EchoHistoryComponent implements OnInit {
  private doctorHttp = inject(DoctorHttpService);
  private indexHttp = inject(IndexHttpService);
  private toast = inject(ToastService);
  private translationService = inject(TranslationService);
  private dialog = inject(MatDialog);
  private route = inject(ActivatedRoute);

  echoData: any = null;
  heartVisualizationData: PatientEchoData | null = null;
  loading = true;
  error: string | null = null;
  patientId: string | number | null = null;
  searchPatientId: string | number = '';

  // LLM Report data
  llmReportData: any = null;
  llmReportText: string = '';
  hasLlmReport: boolean = false;

  // Processed data for display
  patientInfo: any = null;
  visitDates: string[] = []; // sorted descending
  visitsByDate: { [date: string]: any[] } = {};
  selectedDate: string = '';

  ngOnInit(): void {
    // بررسی پارامترهای مسیر (مثل: /echo-history/2)
    const routeId = this.route.snapshot.paramMap.get('id');

    // بررسی کوئری پارامترها (مثل: /echo-history?patientId=2)
    const queryId = this.route.snapshot.queryParamMap.get('patientId');

    const idFromUrl = routeId || queryId;

    if (idFromUrl) {
      // اگر آیدی در URL بود، آن را در اینپوت قرار داده و سرچ را اجرا کن
      this.searchPatientId = idFromUrl;
      this.searchPatient();
    } else {
      // اگر آیدی در URL نبود، صفحه به صورت پیش‌فرض (خالی) لود شود
      this.echoData = null;
      this.loading = false;
    }
  }

  searchPatient(): void {
    const id = Number(this.searchPatientId);
    if (isNaN(id)) {
      this.toast.error(this.getTranslation('pleaseEnterValidPatientId'));
      return;
    }
    this.patientId = id;
    this.loadEchoHistory();
  }

  loadEchoHistory(): void {
    if (this.patientId === null) {
      this.echoData = null;
      this.patientInfo = null;
      this.visitDates = [];
      this.visitsByDate = {};
      this.selectedDate = '';
      this.heartVisualizationData = null;
      this.hasLlmReport = false;
      this.llmReportText = '';
      this.loading = false;
      return;
    }

    this.loading = true;
    this.error = null;
    this.echoData = null;
    this.patientInfo = null;
    this.visitDates = [];
    this.visitsByDate = {};
    this.selectedDate = '';
    this.heartVisualizationData = null;
    this.hasLlmReport = false;
    this.llmReportText = '';

    this.doctorHttp.getEchoHistoryByPatient(this.patientId).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.echoData = response.data;
          this.processEchoData();
        } else {
          this.echoData = null;
          this.error = this.getTranslation('noEchoHistoryFoundForPatient');
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching echo history:', err);
        this.error = this.getTranslation('errorFetchingEchoHistory');
        this.loading = false;
      },
    });
  }

  private processEchoData(): void {
    if (!this.echoData) return;
    this.patientInfo = this.echoData.patient_info || {};
    const visits = this.echoData.visits || {};
    this.visitDates = Object.keys(visits).sort(
      (a, b) => new Date(b).getTime() - new Date(a).getTime(),
    );
    this.visitsByDate = visits;
    if (this.visitDates.length > 0) {
      this.selectedDate = this.visitDates[0];
    }

    this.heartVisualizationData = this.transformToHeartVisualizationData();

    if (this.patientInfo?.id && this.selectedDate) {
      this.loadLlmReport(this.patientInfo.id, this.selectedDate);
    }
  }

  refresh(): void {
    this.loadEchoHistory();
  }

  getVisitList(date: string): any[] {
    return this.visitsByDate[date] || [];
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  // Helper to check if a value is boolean (to hide in UI)
  isBoolean(val: any): boolean {
    return typeof val === 'boolean';
  }

  getMeasurementImages(frameUrl: string, previewUrl: string): string[] {
    return [frameUrl, previewUrl].filter(u => !!u);
  }

  viewEchoFile(address: string, allImages?: string[], startIndex?: number): void {
    if (!address && (!allImages || allImages.length === 0)) return;
    const data: ImageViewerData = allImages && allImages.length > 0
      ? { images: allImages, currentIndex: startIndex ?? 0 }
      : { imageUrl: address };
    const isMobile = window.innerWidth <= 600;
    this.dialog.open(ImageViewerDialogComponent, {
      data,
      width: isMobile ? '100vw' : '92vw',
      maxWidth: isMobile ? '100vw' : '800px',
      height: isMobile ? '100dvh' : 'auto',
      maxHeight: isMobile ? '100dvh' : '90vh',
      panelClass: isMobile ? ['gallery-dialog-panel', 'gallery-dialog-mobile'] : 'gallery-dialog-panel',
    });
  }

  // ── LLM Report ─────────────────────────────────────────────
  private loadLlmReport(patientId: string, visitDate: string): void {
    this.indexHttp.getPatientReportText(patientId, visitDate).subscribe({
      next: (response: any) => {
        // پنل دکتر: گزارش فنی/بالینی (doctor_report) نشون داده می‌شه، نه گزارش ساده‌شده‌ی بیمار
        if (response.success && response.doctor_report) {
          this.llmReportText = response.doctor_report;
          this.hasLlmReport = true;
          this.llmReportData = response;
        } else {
          this.hasLlmReport = false;
          this.llmReportText = '';
        }
      },
      error: () => {
        this.hasLlmReport = false;
        this.llmReportText = '';
      },
    });
  }

  onDateChange(newDate: string): void {
    this.selectedDate = newDate;
    if (this.patientInfo?.id) {
      this.loadLlmReport(this.patientInfo.id, newDate);
    }
  }

  viewFullHtmlReport(): void {
    if (!this.patientInfo?.id || !this.selectedDate) return;
    const htmlUrl = this.indexHttp.getPatientReportHtmlUrl(this.patientInfo.id, this.selectedDate);
    window.open(htmlUrl, '_blank');
  }

  downloadReportPdf(): void {
    this.toast.error('قابلیت دانلود PDF به زودی اضافه خواهد شد');
  }

  // ── Heart Visualization (همان تبدیل داشبورد کاربر) ─────────
  private transformToHeartVisualizationData(): PatientEchoData | null {
    if (!this.echoData || !this.echoData.patient_info) return null;

    const patientInfo = this.echoData.patient_info;

    // Find fuzzy_summary for aggregated data and score
    let fuzzySummary: any = null;
    let aggregatedData: any = null;

    if (this.echoData.visits) {
      for (const date in this.echoData.visits) {
        const visits = this.echoData.visits[date];
        const summary = visits.find((v: any) => v.type === 'fuzzy_summary');
        if (summary) {
          fuzzySummary = summary.result;
          aggregatedData = summary.aggregated_data;
          break;
        }
      }
    }

    let lvid_d: number | undefined;
    let lvid_s: number | undefined;
    let ivs: number | undefined;
    let pw: number | undefined;
    let la_volume: number | undefined;
    let ra_volume: number | undefined;
    let aortic_root: number | undefined;
    let aortic_asc: number | undefined;
    let lv_edv: number | undefined;
    let lv_esv: number | undefined;

    // Use aggregated_data if available (most accurate)
    if (aggregatedData) {
      if (aggregatedData.lv_diameter_processed !== undefined) {
        const val = parseFloat(aggregatedData.lv_diameter_processed);
        lvid_d = val > 10 ? val / 10 : val; // If > 10, assume mm, convert to cm
      }
      if (aggregatedData.ivs_thickness_processed !== undefined) {
        ivs = parseFloat(aggregatedData.ivs_thickness_processed);
      }
      if (aggregatedData.pw_thickness_processed !== undefined) {
        pw = parseFloat(aggregatedData.pw_thickness_processed);
      }
      if (aggregatedData.la_volume_processed !== undefined) {
        la_volume = parseFloat(aggregatedData.la_volume_processed);
      }
      if (aggregatedData.ra_volume_processed !== undefined) {
        ra_volume = parseFloat(aggregatedData.ra_volume_processed);
      }
      if (aggregatedData.aortic_root_processed !== undefined) {
        const val = parseFloat(aggregatedData.aortic_root_processed);
        aortic_root = val > 10 ? val / 10 : val;
      }
      if (aggregatedData.aortic_asc_processed !== undefined) {
        const val = parseFloat(aggregatedData.aortic_asc_processed);
        aortic_asc = val > 10 ? val / 10 : val;
      }
      if (aggregatedData.lv_edv_processed !== undefined) {
        lv_edv = parseFloat(aggregatedData.lv_edv_processed);
      }
    }

    // Fallback: Extract from individual visit measurements
    if (!lvid_d || !lvid_s || !ivs || !pw) {
      if (this.echoData.visits) {
        for (const date in this.echoData.visits) {
          const visits = this.echoData.visits[date];

          visits.forEach((visit: any) => {
            if (visit.type === 'fuzzy_summary') return;

            if (visit.measurements && Array.isArray(visit.measurements)) {
              visit.measurements.forEach((m: any) => {
                const name = m.measurement_name?.toLowerCase() || '';
                const event = m.event_name?.toLowerCase() || '';
                const value = parseFloat(m.value);

                if (name.includes('lvid') && event.includes('diastol')) {
                  if (!lvid_d) lvid_d = value > 10 ? value / 10 : value;
                }
                if (name.includes('lvid') && event.includes('sistol')) {
                  if (!lvid_s) lvid_s = value > 10 ? value / 10 : value;
                }
                if (name.includes('ivs')) {
                  if (!ivs) ivs = value;
                }
                if (name.includes('lvpw') || name.includes('pw')) {
                  if (!pw) pw = value;
                }
                if (name.includes('la') && !name.includes('plax')) {
                  if (!la_volume && visit.a4c_volume?.areas_cm2?.left_atrium) {
                    la_volume = visit.a4c_volume.areas_cm2.left_atrium;
                  }
                }
                if (name.includes('ra') && !name.includes('plax')) {
                  if (!ra_volume && visit.a4c_volume?.areas_cm2?.right_atrium) {
                    ra_volume = visit.a4c_volume.areas_cm2.right_atrium;
                  }
                }
                if (name.includes('aortic_root') || name.includes('aorta_root')) {
                  if (!aortic_root) aortic_root = value > 10 ? value / 10 : value;
                }
                if (name.includes('aorta') && !name.includes('root')) {
                  if (!aortic_asc) aortic_asc = value > 10 ? value / 10 : value;
                }
              });
            }

            if (visit.lv_volume?.area_cm2 && !lv_edv) {
              lv_edv = visit.lv_volume.area_cm2;
            }
          });
        }
      }
    }

    // Calculate EF if we have EDV and ESV, or estimate from LVID
    let ef: number | undefined;
    if (lv_edv && lv_esv) {
      ef = ((lv_edv - lv_esv) / lv_edv) * 100;
    } else if (lvid_d && lvid_s) {
      // Teichholz formula for EF estimation
      const edv = (7 * Math.pow(lvid_d, 3)) / (2.4 + lvid_d);
      const esv = (7 * Math.pow(lvid_s, 3)) / (2.4 + lvid_s);
      ef = ((edv - esv) / edv) * 100;
      lv_edv = edv;
      lv_esv = esv;
    }

    const score    = fuzzySummary?.score !== undefined ? parseFloat(fuzzySummary.score) : undefined;
    const category = fuzzySummary?.category?.toLowerCase() || undefined;

    const weight = parseFloat(patientInfo.weight);
    const height = parseFloat(patientInfo.height);
    const age    = patientInfo.age ? parseInt(patientInfo.age, 10) : undefined;

    return {
      patient_info: {
        id:           patientInfo.id      || undefined,
        gender:       patientInfo.gender  || undefined,
        weight:       isNaN(weight)  ? undefined : weight,
        height:       isNaN(height)  ? undefined : height,
        age:          age,
        smoker:       patientInfo.smoker       ?? undefined,
        diabetic:     patientInfo.diabetic     ?? undefined,
        hypertensive: patientInfo.hypertensive ?? undefined,
      },
      lvid_d,
      lvid_s,
      ivs,
      pw,
      la_volume,
      ra_volume,
      aortic_root,
      aortic_asc,
      lv_edv,
      lv_esv,
      ef,
      score,
      category: category || undefined,
    };
  }
}
