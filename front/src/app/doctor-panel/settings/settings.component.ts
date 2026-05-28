import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-doctor-settings',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
  ],
  template: `
    <div class="settings-container animate__animated animate__fadeIn">
      <header class="page-header mb-4">
        <h1 class="fw-bold mb-1">تنظیمات</h1>
        <p class="text-muted small mb-0">تنظیمات پنل پزشک</p>
      </header>
      
      <mat-card class="settings-card shadow-sm">
        <mat-card-content>
          <p>به زودی...</p>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .settings-container {
      max-width: 900px;
      margin: 0 auto;
      
      .settings-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
      }
    }
  `]
})
export class DoctorSettingsComponent {}