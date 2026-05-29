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
    MatSelectModule
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

  echoData: any = null;
  userAppointments: any[] = [];
  loading = true;
  error: string | null = null;

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
  }

  refresh(): void {
    this.loading = true;
    this.error = null;
    this.echoData = null;
    this.userAppointments = [];
    this.loadUserData();
  }

  getVisitList(date: string): any[] {
    return this.visitsByDate[date] || [];
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'pending': return '#f59e0b';
      case 'confirmed': return '#10b981';
      case 'cancelled': return '#ef4444';
      case 'completed': return '#6366f1';
      default: return '#94a3b8';
    }
  }

  viewEchoFile(address: string): void {
    if (address) {
      // For user dashboard, we can open the file directly via URL (assuming it's public)
      // But we don't have the doctorHttp service; we can just open the address if it's a full URL,
      // or we need to construct it. For simplicity, we'll just open it in a new tab.
      window.open(address, '_blank');
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
}