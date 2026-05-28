import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { TranslationService } from '../../../@shared/services/translation.service';

export interface StatusDialogData {
  status?: any;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-status-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
  template: `
    <div class="status-dialog" [dir]="translationService.getDirection()">
      <h2 mat-dialog-title>
        {{ mode === 'add' ? getTranslation('addStatus') : getTranslation('editStatus') }}
      </h2>

      <form [formGroup]="statusForm" (ngSubmit)="onSubmit()" class="dialog-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('title') }} (English)</mat-label>
          <input matInput formControlName="title" placeholder="e.g. active" />
          <mat-error *ngIf="statusForm.get('title')?.hasError('required')">
            {{ getTranslation('titleRequired') || 'عنوان الزامی است' }}
          </mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('label') }} (Persian)</mat-label>
          <input matInput formControlName="label" placeholder="مثلا فعال" />
          <mat-error *ngIf="statusForm.get('label')?.hasError('required')">
            {{ getTranslation('labelRequired') || 'برچسب الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="dialog-actions">
          <button mat-button type="button" (click)="onCancel()">{{ getTranslation('cancel') }}</button>
          <button
            mat-raised-button
            color="primary"
            type="submit"
            [disabled]="statusForm.invalid"
          >
            {{ getTranslation('save') }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .status-dialog {
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
export class StatusDialogComponent implements OnInit {
  statusForm: FormGroup;
  mode: 'add' | 'edit' = 'add';

  private fb = inject(FormBuilder);
  public translationService = inject(TranslationService);

  constructor(
    public dialogRef: MatDialogRef<StatusDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: StatusDialogData
  ) {
    this.mode = data.mode;
    this.statusForm = this.fb.group({
      title: ['', Validators.required],
      label: ['', Validators.required],
    });

    if (this.mode === 'edit' && data.status) {
      this.statusForm.patchValue({
        title: data.status.title,
        label: data.status.label,
      });
    }
  }

  ngOnInit(): void {}

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onSubmit(): void {
    if (this.statusForm.valid) {
      this.dialogRef.close({
        mode: this.mode,
        data: this.statusForm.value,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
