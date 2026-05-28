import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { PanelHttpService } from '../../panel-http.service';
import { TranslationService } from '../../../@shared/services/translation.service';
import { PanelService } from '../../panel.service';

export interface OrganizationServiceDialogData {
  orgService?: any;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-organization-service-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
  ],
  template: `
    <div class="org-service-dialog" [dir]="translationService.getDirection()">
      <h2 mat-dialog-title>
        {{ mode === 'add' ? getTranslation('addService') : getTranslation('editService') }}
      </h2>

      <form [formGroup]="serviceForm" (ngSubmit)="onSubmit()" class="dialog-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('serviceTitle') || 'عنوان سرویس' }}</mat-label>
          <input matInput formControlName="title" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('duration') }}</mat-label>
          <input matInput type="date" formControlName="exact_duration" />
          <mat-error *ngIf="serviceForm.get('exact_duration')?.hasError('required')">
            {{ getTranslation('durationRequired') || 'تاریخ الزامی است' }}
          </mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('price') }}</mat-label>
          <input matInput type="number" formControlName="organization_price" />
          <mat-error *ngIf="serviceForm.get('organization_price')?.hasError('required')">
            {{ getTranslation('priceRequired') || 'قیمت الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="dialog-actions">
          <button mat-button type="button" (click)="onCancel()">
            {{ getTranslation('cancel') }}
          </button>
          <button mat-raised-button color="primary" type="submit" [disabled]="serviceForm.invalid">
            {{ getTranslation('save') }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .org-service-dialog {
        padding: 20px;
        min-width: 400px;
        @media (max-width: 768px) {
          min-width: unset;
          width: 100%;
        }
      }
      .dialog-form {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .full-width {
        width: 100%;
      }
      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 20px;
      }
      .search-container {
        padding: 8px 16px;
        position: sticky;
        top: 0;
        background: white;
        z-index: 1;
        border-bottom: 1px solid #eee;
      }
      .search-input {
        width: 100%;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
        outline: none;
      }
    `,
  ],
})
export class OrganizationServiceDialogComponent implements OnInit {
  serviceForm: FormGroup;
  services: any[] = [];
  filteredServices: any[] = [];
  mode: 'add' | 'edit' = 'add';
  serviceTitle: any = '';

  private fb = inject(FormBuilder);
  private panelHttp = inject(PanelHttpService);
  public translationService = inject(TranslationService);

  constructor(
    public dialogRef: MatDialogRef<OrganizationServiceDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: OrganizationServiceDialogData,
  ) {
    this.mode = data.mode;
    this.serviceForm = this.fb.group({
      service_id: [null],
      title: [this.serviceTitle],
      exact_duration: [null, Validators.required],
      organization_price: [null, Validators.required],
    });

    if (this.mode === 'edit' && data.orgService) {
      let duration = data.orgService.exact_duration;
      if (duration && duration.includes('T')) {
        duration = duration.split('T')[0];
      } else if (duration && duration.includes(' ')) {
        duration = duration.split(' ')[0];
      }

      this.serviceTitle = data.orgService.title || data.orgService.service_title || '';

      this.serviceForm.patchValue({
        service_id: data.orgService.service_id,
        title: this.serviceTitle,
        exact_duration: duration,
        organization_price: data.orgService.organization_price,
      });
    }
  }

  ngOnInit(): void {
    this.loadServices();
  }

  loadServices() {
    this.panelHttp.getServiceList({ is_paginate: false }).subscribe((res) => {
      if (res.success) {
        this.services = res.data;
        this.filteredServices = res.data;
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onSubmit(): void {
    if (this.serviceForm.valid) {
      const formValue = this.serviceForm.value;

      this.dialogRef.close({
        title: formValue.title,
        duration: formValue.exact_duration,
        price: formValue.organization_price,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
