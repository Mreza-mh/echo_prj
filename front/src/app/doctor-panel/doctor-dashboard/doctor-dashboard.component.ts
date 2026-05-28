import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { DoctorHttpService } from '../doctor-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { format, addDays, parseISO } from 'date-fns';

@Component({
  selector: 'app-doctor-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatChipsModule,
    MatDividerModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  templateUrl: './doctor-dashboard.component.html',
  styleUrls: ['./doctor-dashboard.component.scss'],
})
export class DoctorDashboardComponent implements OnInit {
  private doctorHttp = inject(DoctorHttpService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  selectedDate: string = format(new Date(), 'yyyy-MM-dd');
  
  currentAppointment: any = null;
  loading = true;
  error: string | null = null;
  
  scheduleData: any = null;
  allAppointments: any[] = [];
  currentPatientDetails: any = null;

  ngOnInit(): void {
    this.loadDashboardData();
  }

  setDateFilter(daysOffset: number): void {
    this.selectedDate = format(addDays(new Date(), daysOffset), 'yyyy-MM-dd');
    this.loadDashboardData();
  }

  onCustomDateChange(event: any): void {
    const value = event.target.value;
    if (value) {
      this.selectedDate = format(parseISO(value), 'yyyy-MM-dd');
      this.loadDashboardData();
    }
  }

  isDateActive(daysOffset: number): boolean {
    return this.selectedDate === format(addDays(new Date(), daysOffset), 'yyyy-MM-dd');
  }

  refresh(): void {
    this.loading = true;
    this.error = null;
    this.currentAppointment = null;
    this.scheduleData = null;
    this.allAppointments = [];
    this.currentPatientDetails = null;
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    this.doctorHttp.getCalendarDashboard({ date: this.selectedDate }).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.scheduleData = response.data;
          this.processScheduleData();
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching calendar dashboard:', err);
        this.error = 'خطا در دریافت اطلاعات تقویم';
        this.loading = false;
      }
    });

    this.doctorHttp.getCurrentAppointment().subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.currentAppointment = response.data;
          if (response.data.user?.id) {
            this.loadCurrentPatientDetails(response.data.user.id);
          }
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching current appointment:', err);
        this.cdr.markForCheck();
      }
    });
  }

  onDateChange(): void {
    this.loadDashboardData();
  }

  private processScheduleData(): void {
    if (!this.scheduleData) return;
    
    this.allAppointments = [];
    this.scheduleData.timeline?.forEach((staff: any) => {
      staff.appointments?.forEach((app: any) => {
        this.allAppointments.push({
          ...app,
          staff_name: staff.staff_name,
        });
      });
    });
    this.allAppointments.sort((a, b) => a.start.localeCompare(b.start));
    this.cdr.markForCheck();
  }

  private loadCurrentPatientDetails(patientId: string | number): void {
    this.doctorHttp.getEchoHistoryByPatient(patientId).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.currentPatientDetails = response.data;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching patient details:', err);
        this.currentPatientDetails = null;
        this.cdr.markForCheck();
      }
    });
  }

  viewEchoFile(address: string): void {
    if (address) {
      window.open(`/echo-history/file/${address}`, '_blank');
    }
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
}