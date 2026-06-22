import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { TranslationService } from '../../../@shared/services/translation.service';
import { PanelService } from '../../panel.service';

export interface ResourceDialogData {
  resource?: any;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-resource-dialog',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatSelectModule],
  template: `
    <div class="sd" [dir]="translationService.getDirection()">

      <div class="sd-header">
        <div class="sd-title-row">
          <span class="sd-accent-bar"></span>
          <h2 class="sd-title">
            {{ mode === 'add' ? getTranslation('addResource') : getTranslation('editResource') }}
          </h2>
        </div>
        <button class="sd-close-btn" type="button" (click)="onCancel()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <form [formGroup]="resourceForm" (ngSubmit)="onSubmit()" class="sd-form">

        <div class="sd-field-label">{{ getTranslation('name') }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <input matInput formControlName="resource_name" />
          <mat-error *ngIf="resourceForm.get('resource_name')?.hasError('required')">
            {{ getTranslation('nameRequired') || 'نام الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="sd-field-label">{{ getTranslation('type') }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <mat-select formControlName="resource_type">
            <mat-option value="room">{{ getTranslation('room') || 'اتاق' }}</mat-option>
            <mat-option value="device">{{ getTranslation('device') || 'دستگاه' }}</mat-option>
            <mat-option value="equipment">{{ getTranslation('equipment') || 'تجهیزات' }}</mat-option>
            <mat-option value="other">{{ getTranslation('other') || 'سایر' }}</mat-option>
          </mat-select>
          <mat-error *ngIf="resourceForm.get('resource_type')?.hasError('required')">
            {{ getTranslation('typeRequired') || 'نوع الزامی است' }}
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
    .sd { background: var(--bg-secondary); color: var(--text-primary); width: 100%; display: flex; flex-direction: column; }
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
    .sd-mat-field ::ng-deep .mat-mdc-select-value-text, .sd-mat-field ::ng-deep .mat-mdc-select-placeholder { color: var(--text-primary) !important; font-size: 0.875rem; }
    .sd-mat-field ::ng-deep .mat-mdc-floating-label { color: var(--text-secondary) !important; }
    .sd-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color); }
    .sd-btn { height: 38px; border-radius: 9px; border: none; cursor: pointer; font-size: 0.85rem; font-weight: 700; padding: 0 18px; display: inline-flex; align-items: center; gap: 6px; transition: opacity 0.15s, background 0.15s; svg { width: 15px; height: 15px; } }
    .sd-btn-cancel { background: var(--bg-primary); color: var(--text-secondary); border: 1px solid var(--border-color); &:hover { background: var(--hover-bg); color: var(--text-primary); } }
    .sd-btn-save { background: var(--accent-color); color: #fff; &:hover { opacity: 0.88; } }
  `],
})
export class ResourceDialogComponent implements OnInit {
  resourceForm: FormGroup;
  mode: 'add' | 'edit' = 'add';

  private fb = inject(FormBuilder);
  private panelService = inject(PanelService);
  public translationService = inject(TranslationService);

  constructor(
    public dialogRef: MatDialogRef<ResourceDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ResourceDialogData
  ) {
    this.mode = data.mode;
    this.resourceForm = this.fb.group({
      resource_name: ['', Validators.required],
      resource_type: ['', Validators.required],
    });
    if (this.mode === 'edit' && data.resource) {
      this.resourceForm.patchValue({ resource_name: data.resource.resource_name, resource_type: data.resource.resource_type });
    }
  }

  ngOnInit(): void {}

  getTranslation(key: string): string { return this.translationService.getTranslation(key); }

  onSubmit(): void {
    if (this.resourceForm.valid) {
      this.dialogRef.close({ mode: this.mode, data: this.resourceForm.value });
    }
  }

  onCancel(): void { this.dialogRef.close(); }
}
