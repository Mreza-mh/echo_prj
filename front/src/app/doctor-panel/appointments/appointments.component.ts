import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { DoctorHttpService } from '../doctor-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';

@Component({
  selector: 'app-appointments',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDividerModule,
  ],
  templateUrl: './appointments.component.html',
  styleUrls: ['./appointments.component.scss'],
})
export class AppointmentsComponent implements OnInit {
  private doctorHttp = inject(DoctorHttpService);
  private toast = inject(ToastService);
  private translationService = inject(TranslationService);

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  appointments: any[] = [];
  loading = true;
  error: string | null = null;

  ngOnInit(): void {
    this.loadAppointments();
  }

  refresh(): void {
    this.loading = true;
    this.error = null;
    this.appointments = [];
    this.loadAppointments();
  }

  private loadAppointments(): void {
    this.doctorHttp.getAppointments({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.appointments = Array.isArray(response.data) ? response.data : [];
        } else {
          this.appointments = [];
        }
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Error fetching appointments:', err);
        this.error = this.translationService.getTranslation('failedToLoadAppointments');
        this.loading = false;
      }
    });
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'pending': return 'var(--warning-color)';
      case 'confirmed': return 'var(--success-color)';
      case 'cancelled': return 'var(--error-color)';
      case 'completed': return 'var(--accent-color)';
      default: return '#94a3b8';
    }
  }

  viewAppointment(id: number | string): void {
    // Navigate to appointment details or open in modal
    window.open(`/appointment?edit_id=${id}`, '_blank');
  }
}