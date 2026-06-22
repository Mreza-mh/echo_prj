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
  imports: [CommonModule, ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatSelectModule],
  template: `
    <div class="sd" [dir]="translationService.getDirection()">

      <div class="sd-header">
        <div class="sd-title-row">
          <span class="sd-accent-bar"></span>
          <h2 class="sd-title">
            {{ mode === 'add' ? getTranslation('addService') : getTranslation('editService') }}
          </h2>
        </div>
        <button class="sd-close-btn" type="button" (click)="onCancel()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <form [formGroup]="serviceForm" (ngSubmit)="onSubmit()" class="sd-form">

        <div class="sd-field-label">{{ getTranslation('serviceTitle') || 'عنوان سرویس' }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <input matInput formControlName="title" />
        </mat-form-field>

        <div class="sd-field-label">{{ getTranslation('duration') }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <input matInput type="date" formControlName="exact_duration" />
          <mat-error *ngIf="serviceForm.get('exact_duration')?.hasError('required')">
            {{ getTranslation('durationRequired') || 'تاریخ الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="sd-field-label">{{ getTranslation('price') }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <input matInput type="number" formControlName="organization_price" />
          <mat-error *ngIf="serviceForm.get('organization_price')?.hasError('required')">
            {{ getTranslation('priceRequired') || 'قیمت الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="sd-actions">
          <button class="sd-btn sd-btn-cancel" type="button" (click)="onCancel()">{{ getTranslation('cancel') }}</button>
          <button class="sd-btn sd-btn-save" type="submit">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
            </svg>
            {{ getTranslation('save') }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [`
      .sd { background: var(--bg-secondary); color: var(--text-primary);  width: 100%; display: flex; flex-direction: column; }
      .sd-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px 16px; border-bottom: 1px solid var(--border-color); }
    .sd-title-row { display: flex; align-items: center; gap: 10px; }
    .sd-accent-bar { display: block; width: 4px; height: 22px; background: var(--accent-color); border-radius: 3px; flex-shrink: 0; }
    .sd-title { font-size: 1rem; font-weight: 800; margin: 0; letter-spacing: -0.02em; }
    .sd-close-btn { width: 32px; height: 32px; border: none; background: transparent; cursor: pointer; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); transition: background 0.15s; svg { width: 16px; height: 16px; } &:hover { background: var(--hover-bg); color: var(--text-primary); } }
    .sd-form { padding: 20px 24px 24px; display: flex; flex-direction: column; gap: 4px; }
    .sd-field-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-secondary); margin-bottom: 6px; margin-top: 14px; &:first-child { margin-top: 0; } }
    .sd-mat-field { width: 100%; }
    .sd-mat-field ::ng-deep .mat-mdc-text-field-wrapper { background: var(--bg-primary) !important; border-radius: 10px !important; }
    .sd-mat-field ::ng-deep .mdc-notched-outline__leading, .sd-mat-field ::ng-deep .mdc-notched-outline__notch, .sd-mat-field ::ng-deep .mdc-notched-outline__trailing { border-color: var(--border-color) !important; }
    .sd-mat-field ::ng-deep .mat-mdc-input-element { color: var(--text-primary) !important; font-size: 0.875rem; }
    .sd-mat-field ::ng-deep .mat-mdc-floating-label { color: var(--text-secondary) !important; }
    .sd-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color); }
    .sd-btn { height: 38px; border-radius: 9px; border: none; cursor: pointer; font-size: 0.85rem; font-weight: 700; padding: 0 18px; display: inline-flex; align-items: center; gap: 6px; transition: opacity 0.15s, background 0.15s; svg { width: 15px; height: 15px; } }
    .sd-btn-cancel { background: var(--bg-primary); color: var(--text-secondary); border: 1px solid var(--border-color); &:hover { background: var(--hover-bg); color: var(--text-primary); } }
    .sd-btn-save { background: var(--accent-color); color: #fff; &:hover { opacity: 0.88; } }
  `],
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
      if (duration?.includes('T')) duration = duration.split('T')[0];
      else if (duration?.includes(' ')) duration = duration.split(' ')[0];
      this.serviceTitle = data.orgService.title || data.orgService.service_title || '';
      this.serviceForm.patchValue({ service_id: data.orgService.service_id, title: this.serviceTitle, exact_duration: duration, organization_price: data.orgService.organization_price });
    }
  }

  ngOnInit(): void { this.loadServices(); }

  loadServices() {
    this.panelHttp.getServiceList({ is_paginate: false }).subscribe((res: any) => {
      if (res.success) { this.services = res.data; this.filteredServices = res.data; }
    });
  }

  getTranslation(key: string): string { return this.translationService.getTranslation(key); }

  onSubmit(): void {
    if (this.serviceForm.valid) {
      const v = this.serviceForm.value;
      this.dialogRef.close({ title: v.title, duration: v.exact_duration, price: v.organization_price });
    }
  }

  onCancel(): void { this.dialogRef.close(); }
}
