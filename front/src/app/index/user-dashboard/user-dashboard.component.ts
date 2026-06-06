import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { IndexHttpService } from '../index-http.service';
import { AuthHTTPService } from '../../auth/auth-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { MatSelectModule } from '@angular/material/select';
import { MatDialogModule } from '@angular/material/dialog';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ImageViewerDialogComponent } from './image-viewer-dialog.component';
import { PatientFormComponent } from '../../@shared/components/patient-form/patient-form.component';
import { HeartVisualizationComponent, PatientEchoData } from '../heart-visualization/heart-visualization';

@Component({
  selector: 'app-user-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatSelectModule,
    MatDialogModule,
    MatTooltipModule,
    ImageViewerDialogComponent,
    PatientFormComponent,
    HeartVisualizationComponent
  ],
  templateUrl: './user-dashboard.component.html',
  styleUrls: ['./user-dashboard.component.scss']
})
export class UserDashboardComponent implements OnInit {
  private indexHttp = inject(IndexHttpService);
  private authHttp = inject(AuthHTTPService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private fb = inject(FormBuilder);
  private translationService = inject(TranslationService);
  private dialog = inject(MatDialog);

  echoData: any = null;
  heartVisualizationData: PatientEchoData | null = null;
  userAppointments: any[] = [];
  loading = true;
  error: string | null = null;

  // LLM Report data
  llmReportData: any = null;
  llmReportText: string = '';
  hasLlmReport: boolean = false;

  // Profile
  profileForm!: FormGroup;
  isEditingProfile = false;
  userData: any = {};

  // Processed echo data for display
  patientInfo: any = null;
  visitDates: string[] = [];
  visitsByDate: { [date: string]: any[] } = {};
  selectedDate: string = '';

  ngOnInit(): void {
    this.initProfileForm();
    this.loadUserData();
  }

  private initProfileForm(): void {
    this.profileForm = this.fb.group({
      name: ['', Validators.required],
      birthday: ['', Validators.required],
      phone: [{ value: '', disabled: true }],
      role: [{ value: '', disabled: true }]
    });
  }

  private loadUserData(): void {
    this.loading = true;
    this.error = null;

    // Load user echo history
    this.indexHttp.getUserEchoHistory().subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.echoData = response.data;
          this.processEchoData();
          
          // Load LLM report if patient has visits
          if (this.patientInfo?.id && this.selectedDate) {
            this.loadLlmReport(this.patientInfo.id, this.selectedDate);
          }
        } else {
          this.echoData = null;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching user echo history:', err);
        this.echoData = null;
        this.cdr.markForCheck();
      }
    });

    // Load user appointments
    this.indexHttp.getUserAppointments({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.userAppointments = Array.isArray(response.data) ? response.data : [];
        } else {
          this.userAppointments = [];
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching user appointments:', err);
        this.userAppointments = [];
        this.loading = false;
        this.cdr.markForCheck();
      }
    });

    // Load user profile
    this.authHttp.getMe().subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.userData = response.data;
          this.profileForm.patchValue({
            name: this.userData.name,
            birthday: this.userData.birthday,
            phone: this.userData.mobile,
            role: this.getUserRoleLabel(this.userData.role)
          });
        }
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error loading profile:', error);
        this.toast.error(this.getTranslation('errorLoadingProfile'));
        this.cdr.markForCheck();
      }
    });
  }

  private processEchoData(): void {
    if (!this.echoData) return;
    this.patientInfo = this.echoData.patient_info || {};
    const visits = this.echoData.visits || {};
    this.visitDates = Object.keys(visits).sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
    this.visitsByDate = visits;
    if (this.visitDates.length > 0) {
      this.selectedDate = this.visitDates[0];
    }
    
    // Transform echoData to PatientEchoData format for heart visualization
    this.heartVisualizationData = this.transformToHeartVisualizationData();
    console.log('🫀 Heart visualization data transformed:', this.heartVisualizationData);
  }

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

    // Extract measurements from aggregated_data (preferred) or individual visits
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
      // LV diameter (LVID) - convert mm to cm if needed
      if (aggregatedData.lv_diameter_processed !== undefined) {
        const val = parseFloat(aggregatedData.lv_diameter_processed);
        lvid_d = val > 10 ? val / 10 : val; // If > 10, assume mm, convert to cm
      }
      
      // IVS thickness - convert mm to mm (already in mm)
      if (aggregatedData.ivs_thickness_processed !== undefined) {
        ivs = parseFloat(aggregatedData.ivs_thickness_processed);
      }
      
      // Posterior wall thickness
      if (aggregatedData.pw_thickness_processed !== undefined) {
        pw = parseFloat(aggregatedData.pw_thickness_processed);
      }
      
      // LA volume
      if (aggregatedData.la_volume_processed !== undefined) {
        la_volume = parseFloat(aggregatedData.la_volume_processed);
      }
      
      // RA volume
      if (aggregatedData.ra_volume_processed !== undefined) {
        ra_volume = parseFloat(aggregatedData.ra_volume_processed);
      }
      
      // Aortic root
      if (aggregatedData.aortic_root_processed !== undefined) {
        const val = parseFloat(aggregatedData.aortic_root_processed);
        aortic_root = val > 10 ? val / 10 : val; // If > 10, assume mm, convert to cm
      }
      
      // Aortic ascending
      if (aggregatedData.aortic_asc_processed !== undefined) {
        const val = parseFloat(aggregatedData.aortic_asc_processed);
        aortic_asc = val > 10 ? val / 10 : val;
      }
      
      // LV EDV (End-Diastolic Volume)
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
            if (visit.type === 'fuzzy_summary') return; // Skip summary
            
            if (visit.measurements && Array.isArray(visit.measurements)) {
              visit.measurements.forEach((m: any) => {
                const name = m.measurement_name?.toLowerCase() || '';
                const event = m.event_name?.toLowerCase() || '';
                const value = parseFloat(m.value);
                
                // LVID diastole (End Diastol)
                if (name.includes('lvid') && event.includes('diastol')) {
                  if (!lvid_d) lvid_d = value > 10 ? value / 10 : value;
                }
                
                // LVID systole (End Sistol)
                if (name.includes('lvid') && event.includes('sistol')) {
                  if (!lvid_s) lvid_s = value > 10 ? value / 10 : value;
                }
                
                // IVS (Interventricular Septum)
                if (name.includes('ivs')) {
                  if (!ivs) ivs = value;
                }
                
                // LVPW (Left Ventricular Posterior Wall)
                if (name.includes('lvpw') || name.includes('pw')) {
                  if (!pw) pw = value;
                }
                
                // LA (Left Atrium)
                if (name.includes('la') && !name.includes('plax')) {
                  if (!la_volume && visit.a4c_volume?.areas_cm2?.left_atrium) {
                    la_volume = visit.a4c_volume.areas_cm2.left_atrium;
                  }
                }
                
                // RA (Right Atrium)
                if (name.includes('ra') && !name.includes('plax')) {
                  if (!ra_volume && visit.a4c_volume?.areas_cm2?.right_atrium) {
                    ra_volume = visit.a4c_volume.areas_cm2.right_atrium;
                  }
                }
                
                // Aortic root
                if (name.includes('aortic_root') || name.includes('aorta_root')) {
                  if (!aortic_root) aortic_root = value > 10 ? value / 10 : value;
                }
                
                // Aorta (ascending)
                if (name.includes('aorta') && !name.includes('root')) {
                  if (!aortic_asc) aortic_asc = value > 10 ? value / 10 : value;
                }
              });
            }
            
            // Extract LV volume from lv_volume field
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

    // Get score and category from fuzzy summary
    const score = fuzzySummary?.score !== undefined ? parseFloat(fuzzySummary.score) : undefined;
    const category = fuzzySummary?.category?.toLowerCase() || 'normal';

    return {
      patient_info: {
        id: patientInfo.id || this.userData.id || 'N/A',
        gender: patientInfo.gender || this.userData.gender || 'male',
        weight: parseFloat(patientInfo.weight) || 70,
        height: parseFloat(patientInfo.height) || 170,
        age: this.calculateAge(this.userData.birthday),
        smoker: false,
        diabetic: false,
        hypertensive: false
      },
      lvid_d: lvid_d || 5.0,
      lvid_s: lvid_s || 3.5,
      ivs: ivs || 10,
      pw: pw || 10,
      la_volume: la_volume || 30,
      ra_volume: ra_volume || 35,
      aortic_root: aortic_root || 3.0,
      aortic_asc: aortic_asc,
      lv_edv: lv_edv,
      lv_esv: lv_esv,
      ef: ef || 60,
      score: score || 20,
      category: category
    };
  }

  private calculateAge(birthday: string): number {
    if (!birthday) return 30;
    const birthDate = new Date(birthday);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  }

  refresh(): void {
    this.loading = true;
    this.error = null;
    this.echoData = null;
    this.userAppointments = [];
    this.loadUserData();
  }



  openPatientFormModal(): void {
    const dialogRef = this.dialog.open(PatientFormComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        userId: this.userData?.id
      },
      disableClose: false,
      panelClass: 'patient-form-dialog'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.toast.success('اطلاعات پزشکی با موفقیت ذخیره شد');
        // Optionally refresh data
        this.loadUserData();
      }
    });
  }

  getVisitList(date: string): any[] {
    return this.visitsByDate[date] || [];
  }

  getStatusColor(status: string): string {
    if (!status) return '#94a3b8';
    
    const statusLower = status.toLowerCase();
    
    switch (statusLower) {
      case 'pending':
      case 'در انتظار':
        return '#f59e0b';
      case 'confirmed':
      case 'تایید شده':
        return '#10b981';
      case 'cancelled':
      case 'لغو شده':
        return '#ef4444';
      case 'completed':
      case 'تکمیل شده':
        return '#6366f1';
      default:
        return '#94a3b8';
    }
  }

  viewEchoFile(address: string): void {
    if (address) {
      this.dialog.open(ImageViewerDialogComponent, {
        data: { imageUrl: address },
        width: '90%',
        maxWidth: '600px',
        height: '90%',
        maxHeight: '700px'
      });
    }
  }

  // Profile methods
  toggleEditProfile(): void {
    this.isEditingProfile = !this.isEditingProfile;
    if (this.isEditingProfile) {
      this.profileForm.enable();
    } else {
      this.profileForm.disable();
      // Reload the profile data to discard changes
      this.loadUserData();
    }
  }

  onProfileSubmit(): void {
    if (this.profileForm.valid && !this.isEditingProfile) {
      return;
    }
    if (this.profileForm.invalid) {
      this.toast.error(this.getTranslation('pleaseFillRequiredFields'));
      return;
    }

    const formData = {
      name: this.profileForm.value.name,
      birthday: this.profileForm.value.birthday
    };

    this.authHttp.editProfile(formData).subscribe({
      next: (response) => {
        if (response.success) {
          this.toast.success(this.getTranslation('profileUpdatedSuccessfully'));
          this.toggleEditProfile();
          // Update the userData
          this.userData.name = formData.name;
          this.userData.birthday = formData.birthday;
        } else {
          this.toast.error(response.message || this.getTranslation('errorUpdatingProfile'));
        }
        this.cdr.markForCheck();
      },
      error: (error) => {
        this.toast.error(this.getTranslation('errorConnectingToServer'));
        this.cdr.markForCheck();
      }
    });
  }

  getUserRoleLabel(role: string): string {
    switch (role) {
      case 'super_admin': return 'مدیر ارشد';
      case 'admin': return 'مدیر سیستم';
      case 'user': return 'کاربر عادی';
      default: return role || 'نامشخص';
    }
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  isBoolean(val: any): boolean {
    return typeof val === 'boolean';
  }

  // LLM Report Methods
  private loadLlmReport(patientId: string, visitDate: string): void {
    this.indexHttp.getPatientReportText(patientId, visitDate).subscribe({
      next: (response: any) => {
        if (response.success && response.report_text) {
          this.llmReportText = response.report_text;
          this.hasLlmReport = true;
          this.llmReportData = response;
        } else {
          this.hasLlmReport = false;
          this.llmReportText = '';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.log('No LLM report available for this visit');
        this.hasLlmReport = false;
        this.llmReportText = '';
        this.cdr.markForCheck();
      }
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
    
    const htmlUrl = this.indexHttp.getPatientReportHtmlUrl(
      this.patientInfo.id, 
      this.selectedDate
    );
    
    window.open(htmlUrl, '_blank');
  }

  downloadReportPdf(): void {
    // Future implementation for PDF download
    this.toast.error('قابلیت دانلود PDF به زودی اضافه خواهد شد');
  }
}