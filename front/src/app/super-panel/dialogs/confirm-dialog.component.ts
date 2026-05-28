import { Component, Inject, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslationService } from '../../@shared/services/translation.service';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'warn' | 'primary' | 'accent';
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <div class="confirm-dialog" [dir]="getDirection()">
      <div class="dialog-header">
        <mat-icon [class]="'icon-' + (data.type || 'warn')">
          {{ data.type === 'warn' ? 'warning' : 'help' }}
        </mat-icon>
        <h2 mat-dialog-title>{{ data.title }}</h2>
      </div>

      <mat-dialog-content>
        <p>{{ data.message }}</p>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()" aria-label="Cancel action">
          {{ data.cancelText || getTranslation('cancel') }}
        </button>
        <button
          mat-flat-button
          [color]="data.type || 'warn'"
          (click)="onConfirm()"
          aria-label="Confirm action"
        >
          {{ data.confirmText || getTranslation('delete') }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [
    `
      .confirm-dialog {
        padding: 8px;
        min-width: 320px;
        max-width: 450px;
      }

      .dialog-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
        padding: 0 8px;

        mat-icon {
          font-size: 32px;
          width: 32px;
          height: 32px;
        }

        h2 {
          margin: 0;
          font-weight: 600;
          font-size: 1.2rem;
          color: var(--mat-sys-on-surface);
        }
      }

      .icon-warn {
        color: var(--mat-sys-error);
      }

      .icon-primary {
        color: var(--mat-sys-primary);
      }

      .icon-accent {
        color: var(--mat-sys-secondary);
      }

      mat-dialog-content {
        margin-bottom: 24px;
        padding: 0 8px;
        color: var(--mat-sys-on-surface-variant);
        font-size: 0.95rem;
        line-height: 1.6;
        text-align: start;
      }

      p {
        margin: 0;
      }

      mat-dialog-actions {
        gap: 8px;
        padding: 8px 0 0;
      }

      ::ng-deep {
        [dir='rtl'] {
          .dialog-header {
            gap: 16px;
          }
        }
      }
    `,
  ],
})
export class ConfirmDialogComponent {
  public dialogRef = inject(MatDialogRef<ConfirmDialogComponent>);
  public data = inject<ConfirmDialogData>(MAT_DIALOG_DATA);
  private translationService = inject(TranslationService);

  onConfirm(): void {
    this.dialogRef.close(true);
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  getDirection(): 'ltr' | 'rtl' {
    return this.translationService.getDirection();
  }
}
