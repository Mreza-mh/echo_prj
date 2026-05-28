import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTableModule } from '@angular/material/table';
import { IndexHttpService } from '../index-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';

@Component({
  selector: 'app-user-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTableModule,
  ],
  templateUrl: './user-dashboard.component.html',
  styleUrls: ['./user-dashboard.component.scss'],
})
export class UserDashboardComponent implements OnInit {
  private indexHttp = inject(IndexHttpService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  userEchoHistory: any = null;
  userAppointments: any[] = [];
  loading = true;
  error: string | null = null;

  ngOnInit(): void {
    this.loadUserData();
  }

  refresh(): void {
    this.loading = true;
    this.error = null;
    this.userEchoHistory = null;
    this.userAppointments = [];
    this.loadUserData();
  }

  private loadUserData(): void {
    // Load user echo history
    this.indexHttp.getUserEchoHistory().subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.userEchoHistory = response.data;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching user echo history:', err);
        this.userEchoHistory = null;
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
      window.open(`/echo-history/file/${address}`, '_blank');
    }
  }
}