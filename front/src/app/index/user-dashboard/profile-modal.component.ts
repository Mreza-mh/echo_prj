import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ReactiveFormsModule, FormGroup } from '@angular/forms';

@Component({
  selector: 'app-profile-modal',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule
  ],
  template: `
    <div class="profile-modal">
      <div class="modal-header">
        <h2>
          <span class="icon">👤</span>
          پروفایل کاربری
        </h2>
        <button type="button" class="close-btn" (click)="dialogRef.close()">
          <span class="icon">✕</span>
        </button>
      </div>

      <div class="modal-content">
        <form [formGroup]="data.profileForm">
          <div class="form-grid">
            <div class="form-field full-width">
              <label class="form-label">
                <span class="label-icon">📛</span>
                نام و نام خانوادگی
              </label>
              <input 
                type="text" 
                class="form-input" 
                formControlName="name" 
                placeholder="نام خود را وارد کنید">
            </div>

            <div class="form-field full-width">
              <label class="form-label">
                <span class="label-icon">🎂</span>
                تاریخ تولد
              </label>
              <input 
                type="date" 
                class="form-input" 
                formControlName="birthday" 
                placeholder="انتخاب تاریخ">
            </div>

            <div class="form-field full-width">
              <label class="form-label">
                <span class="label-icon">📱</span>
                شماره موبایل
              </label>
              <input 
                type="text" 
                class="form-input" 
                formControlName="phone" 
                [disabled]="true"
                dir="ltr"
                style="text-align: left;">
            </div>

            <div class="form-field full-width">
              <label class="form-label">
                <span class="label-icon">🔐</span>
                نقش کاربری
              </label>
              <input 
                type="text" 
                class="form-input" 
                formControlName="role" 
                [disabled]="true">
            </div>
          </div>
        </form>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" (click)="dialogRef.close()">
          <span class="icon">✕</span>
          انصراف
        </button>
        <button type="button" class="btn btn-primary" (click)="save()">
          <span class="icon">💾</span>
          ذخیره تغییرات
        </button>
      </div>
    </div>
  `,
  styles: [`
    .profile-modal {
      direction: rtl;
      font-family: 'Tahoma', 'Arial', sans-serif;

      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px 28px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        margin: -24px -24px 0 -24px;

        h2 {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 0;
          color: white;
          font-size: 22px;
          font-weight: 700;

          .icon {
            font-size: 28px;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
          }
        }

        .close-btn {
          background: rgba(255, 255, 255, 0.1);
          border: none;
          border-radius: 8px;
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s;
          color: white;

          .icon {
            font-size: 20px;
          }

          &:hover {
            background: rgba(255, 255, 255, 0.2);
          }
        }
      }

      .modal-content {
        padding: 32px 28px;
        min-height: 320px;
        overflow-y: auto;
      }

      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px 20px;

        .full-width {
          grid-column: span 2;
        }

        @media (max-width: 768px) {
          grid-template-columns: 1fr;

          .full-width {
            grid-column: span 1;
          }
        }
      }

      .form-field {
        display: flex;
        flex-direction: column;
        gap: 8px;

        .form-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #334155;
          margin: 0;

          .label-icon {
            font-size: 18px;
          }
        }

        .form-input {
          width: 100%;
          padding: 12px 16px;
          font-size: 15px;
          font-family: inherit;
          color: #1e293b;
          background-color: #f8fafc;
          border: 2px solid #cbd5e1;
          border-radius: 8px;
          outline: none;
          transition: all 0.3s ease;
          direction: rtl;
          text-align: right;

          &::placeholder {
            color: #94a3b8;
          }

          &:hover:not(:disabled) {
            background-color: #f1f5f9;
            border-color: #94a3b8;
          }

          &:focus {
            background-color: #ffffff;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
          }

          &:disabled {
            color: #64748b;
            background-color: #f1f5f9;
            cursor: not-allowed;
            opacity: 0.7;
          }
        }
      }

      .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        padding: 20px 28px 24px;
        border-top: 2px solid #e2e8f0;
        margin: 0 -24px -24px -24px;
        background: linear-gradient(to bottom, #ffffff 0%, #f8fafc 100%);
      }

      .btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 0 24px;
        height: 44px;
        font-size: 15px;
        font-weight: 600;
        border-radius: 10px;
        border: none;
        outline: none;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        font-family: inherit;

        .icon {
          font-size: 18px;
        }

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }

        &:active {
          transform: translateY(0);
        }

        &.btn-primary {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;

          &:hover {
            background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
          }
        }

        &.btn-secondary {
          background: #f1f5f9;
          color: #475569;
          border: 2px solid #e2e8f0;

          &:hover {
            background: #e2e8f0;
            border-color: #cbd5e1;
          }
        }
      }

      @media (max-width: 768px) {
        .modal-header {
          padding: 20px 20px;

          h2 {
            font-size: 20px;

            .icon {
              font-size: 24px;
            }
          }
        }

        .modal-content {
          padding: 24px 20px;
        }

        .modal-footer {
          flex-direction: column-reverse;
          padding: 16px 20px 20px;

          .btn {
            width: 100%;
          }
        }
      }
    }
  `]
})
export class ProfileModalComponent {
  constructor(
    public dialogRef: MatDialogRef<ProfileModalComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {}

  save(): void {
    if (this.data.profileForm.valid) {
      this.dialogRef.close(this.data.profileForm.value);
    }
  }
}
