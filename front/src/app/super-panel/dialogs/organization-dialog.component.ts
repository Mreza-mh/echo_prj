import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Organization } from '../models/organization.model';
import { TranslationService } from '../../@shared/services/translation.service';

export interface OrganizationDialogData {
  organization?: Organization;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-organization-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="dialog-container" [dir]="getDirection()">
      <h2 mat-dialog-title>
        {{ getTranslation(data.mode === 'add' ? 'addOrganization' : 'editOrganization') }}
      </h2>

      <mat-dialog-content>
        <form [formGroup]="organizationForm" class="dialog-form">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('name') }}</mat-label>
            <input matInput formControlName="name" [placeholder]="getTranslation('name')">
            <mat-error *ngIf="organizationForm.get('name')?.hasError('required')">
              {{ getTranslation('required') }}
            </mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('businessType') }}</mat-label>
            <mat-select formControlName="business_type">
              <mat-option value="clinic">{{ getTranslation('clinic') }}</mat-option>
              <mat-option value="corporation">{{ getTranslation('corporation') }}</mat-option>
              <mat-option value="llc">{{ getTranslation('llc') }}</mat-option>
              <mat-option value="partnership">{{ getTranslation('partnership') }}</mat-option>
              <mat-option value="sole_proprietorship">{{ getTranslation('soleProprietorship') }}</mat-option>
              <mat-option value="nonprofit">{{ getTranslation('nonprofit') }}</mat-option>
            </mat-select>
            <mat-error *ngIf="organizationForm.get('business_type')?.hasError('required')">
              {{ getTranslation('required') }}
            </mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('phone') }}</mat-label>
            <input matInput formControlName="phone" [placeholder]="getTranslation('phone')">
            <mat-error *ngIf="organizationForm.get('phone')?.hasError('required')">
              {{ getTranslation('required') }}
            </mat-error>
            <mat-error *ngIf="organizationForm.get('phone')?.hasError('pattern')">
              {{ getTranslation('invalidPhone') }}
            </mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('address') }}</mat-label>
            <textarea matInput formControlName="address" [placeholder]="getTranslation('address')" rows="3"></textarea>
            <mat-error *ngIf="organizationForm.get('address')?.hasError('required')">
              {{ getTranslation('required') }}
            </mat-error>
          </mat-form-field>
        </form>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()">{{ getTranslation('cancel') }}</button>
        <button mat-raised-button color="primary" (click)="onSubmit()" [disabled]="organizationForm.invalid || isLoading">
          <mat-spinner *ngIf="isLoading" diameter="20" class="inline-spinner"></mat-spinner>
          <span>{{ getTranslation('save') }}</span>
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
    .inline-spinner {
      display: inline-block;
      margin-right: 8px;
    }
    [dir='rtl'] .inline-spinner {
      margin-right: 0;
      margin-left: 8px;
    }
  `]
})
export class OrganizationDialogComponent implements OnInit {
  private fb = inject(FormBuilder);
  private translationService = inject(TranslationService);
  
  organizationForm: FormGroup;
  isLoading = false;

  constructor(
    public dialogRef: MatDialogRef<OrganizationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: OrganizationDialogData
  ) {
    this.organizationForm = this.fb.group({
      name: ['', Validators.required],
      business_type: ['', Validators.required],
      address: ['', Validators.required],
      phone: ['', [Validators.required, Validators.pattern(/^[0-9+]+$/)]],
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  getDirection(): 'ltr' | 'rtl' {
    return this.translationService.getDirection();
  }

  ngOnInit(): void {
    if (this.data.organization) {
      this.organizationForm.patchValue(this.data.organization);
    }
  }

  onSubmit(): void {
    if (this.organizationForm.valid) {
      this.dialogRef.close({
        mode: this.data.mode,
        data: this.organizationForm.value,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
