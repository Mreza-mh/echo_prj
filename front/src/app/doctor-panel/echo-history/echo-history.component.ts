import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DoctorHttpService } from '../doctor-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';

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
  ],
  templateUrl: './echo-history.component.html',
  styleUrls: ['./echo-history.component.scss'],
})
export class EchoHistoryComponent implements OnInit {
  private doctorHttp = inject(DoctorHttpService);
  private toast = inject(ToastService);

  echoHistories: any[] = [];
  loading = true;
  error: string | null = null;

  ngOnInit(): void {
    this.loadEchoHistories();
  }

  refresh(): void {
    this.loading = true;
    this.error = null;
    this.echoHistories = [];
    this.loadEchoHistories();
  }

  private loadEchoHistories(): void {
    // For now, we load the current user's echo history
    this.doctorHttp.getEchoHistory().subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.echoHistories = Array.isArray(response.data) ? response.data : [response.data];
        } else {
          this.echoHistories = [];
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching echo histories:', err);
        this.error = 'خطا در دریافت اطلاعات اکوها';
        this.loading = false;
      }
    });
  }

  viewEchoFile(address: string): void {
    if (address) {
      this.doctorHttp.getEchoFile(address).subscribe({
        next: (blob: Blob) => {
          const url = window.URL.createObjectURL(blob);
          window.open(url, '_blank');
        },
        error: (err) => {
          this.toast.error('خطا در دریافت فایل اکو');
        }
      });
    }
  }

  downloadEchoFile(address: string): void {
    if (address) {
      this.doctorHttp.getEchoFile(address).subscribe({
        next: (blob: Blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'echo-file.pdf';
          a.click();
          window.URL.revokeObjectURL(url);
        },
        error: (err) => {
          this.toast.error('خطا در دانلود فایل اکو');
        }
      });
    }
  }
}