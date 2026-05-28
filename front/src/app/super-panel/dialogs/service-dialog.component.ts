import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { Service } from '../models/service.model';
import { TranslationService } from '../../@shared/services/translation.service';

export interface ServiceDialogData {
  service?: Service;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-service-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
  ],
  template: `
    <div class="dialog-container" [dir]="getDirection()">
      <h2 mat-dialog-title>
        <mat-icon>{{ data.mode === 'add' ? 'add' : 'edit' }}</mat-icon>
        {{ getTranslation(data.mode === 'add' ? 'addService' : 'editService') }}
      </h2>

      <mat-dialog-content>
        <form [formGroup]="serviceForm" class="dialog-form">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('title') }}</mat-label>
            <input matInput formControlName="title" [placeholder]="getTranslation('title')">
            <mat-icon matPrefix>medical_services</mat-icon>
            <mat-error *ngIf="serviceForm.get('title')?.hasError('required')">
              {{ getTranslation('required') }}
            </mat-error>
          </mat-form-field>

          <div class="form-row">
            <mat-form-field appearance="outline" class="half-width">
              <mat-label>{{ getTranslation('duration') }} ({{ getTranslation('minutes') }})</mat-label>
              <input matInput type="number" formControlName="default_duration" [placeholder]="getTranslation('duration')">
              <mat-icon matPrefix>schedule</mat-icon>
              <mat-error *ngIf="serviceForm.get('default_duration')?.hasError('required')">
                {{ getTranslation('required') }}
              </mat-error>
              <mat-error *ngIf="serviceForm.get('default_duration')?.hasError('min')">
                {{ getTranslation('minValue') }} 1
              </mat-error>
            </mat-form-field>

            <mat-form-field appearance="outline" class="half-width">
              <mat-label>{{ getTranslation('price') }}</mat-label>
              <input matInput type="number" formControlName="general_price" [placeholder]="getTranslation('price')">
              <mat-icon matPrefix>payments</mat-icon>
              <mat-error *ngIf="serviceForm.get('general_price')?.hasError('required')">
                {{ getTranslation('required') }}
              </mat-error>
              <mat-error *ngIf="serviceForm.get('general_price')?.hasError('min')">
                {{ getTranslation('minValue') }} 0
              </mat-error>
            </mat-form-field>
          </div>
        </form>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()">{{ getTranslation('cancel') }}</button>
        <button mat-raised-button color="primary" (click)="onSubmit()" [disabled]="serviceForm.invalid || isLoading">
          <mat-spinner *ngIf="isLoading" diameter="20" class="inline-spinner"></mat-spinner>
          <span *ngIf="!isLoading">{{ getTranslation('save') }}</span>
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .dialog-container {
      padding: 8px;
    }
    .dialog-form {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding-top: 16px;
    }
    .full-width {
      width: 100%;
    }
    mat-form-field {
      text-align: start;
    }
    .form-row {
      display: flex;
      gap: 16px;
    }
    [dir='rtl'] .form-row {
      flex-direction: row;
    }
    .half-width {
      flex: 1;
    }
    .inline-spinner {
      display: inline-block;
      margin-right: 8px;
    }
    [dir='rtl'] .inline-spinner {
      margin-right: 0;
      margin-left: 8px;
    }
    h2 {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  `]
})
export class ServiceDialogComponent implements OnInit {
  private fb = inject(FormBuilder);
  private translationService = inject(TranslationService);
  
  serviceForm: FormGroup;
  isLoading = false;

  constructor(
    public dialogRef: MatDialogRef<ServiceDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ServiceDialogData
  ) {
    this.serviceForm = this.fb.group({
      title: ['', Validators.required],
      default_duration: [30, [Validators.required, Validators.min(1)]],
      general_price: [0, [Validators.required, Validators.min(0)]],
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  getDirection(): 'ltr' | 'rtl' {
    return this.translationService.getDirection();
  }

  ngOnInit(): void {
    if (this.data.service) {
      const serviceData = { ...this.data.service };
      if (typeof serviceData.default_duration === 'string') {
        serviceData.default_duration = this.timeStringToMinutes(serviceData.default_duration) as any;
      }
      this.serviceForm.patchValue(serviceData);
    }
  }

  private timeStringToMinutes(timeString: string): number {
    const [hours, minutes] = timeString.split(':').map(Number);
    return hours * 60 + minutes;
  }

  private minutesToTimeString(totalMinutes: number): string {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:00`;
  }

  onSubmit(): void {
    if (this.serviceForm.valid) {
      const formData = { ...this.serviceForm.value };
      formData.default_duration = this.minutesToTimeString(formData.default_duration);
      
      this.dialogRef.close({
        mode: this.data.mode,
        data: formData,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
