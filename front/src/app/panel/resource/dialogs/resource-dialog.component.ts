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
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule
  ],
  template: `
    <div class="resource-dialog" [dir]="translationService.getDirection()">
      <h2 mat-dialog-title>
        {{ mode === 'add' ? getTranslation('addResource') : getTranslation('editResource') }}
      </h2>

      <form [formGroup]="resourceForm" (ngSubmit)="onSubmit()" class="dialog-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('name') }}</mat-label>
          <input matInput formControlName="resource_name" />
          <mat-error *ngIf="resourceForm.get('resource_name')?.hasError('required')">
            {{ getTranslation('nameRequired') || 'نام الزامی است' }}
          </mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('type') }}</mat-label>
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

        <div class="dialog-actions">
          <button mat-button type="button" (click)="onCancel()">{{ getTranslation('cancel') }}</button>
          <button
            mat-raised-button
            color="primary"
            type="submit"
            [disabled]="resourceForm.invalid"
          >
            {{ getTranslation('save') }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .resource-dialog {
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
    `,
  ],
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
      this.resourceForm.patchValue({
        resource_name: data.resource.resource_name,
        resource_type: data.resource.resource_type,
      });
    }
  }

  ngOnInit(): void {}

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onSubmit(): void {
    if (this.resourceForm.valid) {
      this.dialogRef.close({
        mode: this.mode,
        data: this.resourceForm.value,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
