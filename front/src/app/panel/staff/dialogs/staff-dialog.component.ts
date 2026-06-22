import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { AuthHTTPService } from '../../../auth/auth-http.service';
import { PanelHttpService } from '../../panel-http.service';
import { TranslationService } from '../../../@shared/services/translation.service';

export interface StaffDialogData {
  staff?: any;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-staff-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatIconModule,
    MatListModule,
  ],
  template: `
    <div class="sd" [dir]="translationService.getDirection()">

      <!-- Header -->
      <div class="sd-header">
        <div class="sd-title-row">
          <span class="sd-accent-bar"></span>
          <h2 class="sd-title">
            {{ mode === 'add' ? getTranslation('addStaff') : getTranslation('editStaff') }}
          </h2>
        </div>
        <button class="sd-close-btn" type="button" (click)="onCancel()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Form -->
      <form [formGroup]="staffForm" (ngSubmit)="onSubmit()" class="sd-form">

        <!-- User search (add mode) -->
        <ng-container *ngIf="mode === 'add'">
          <div class="sd-field-label">{{ getTranslation('searchUser') || 'جستجوی کاربر' }}</div>
          <div class="sd-search-box" [class.has-results]="users.length > 0">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              class="sd-input"
              [formControl]="searchControl"
              [placeholder]="getTranslation('searchUserPlaceholder') || 'نام یا شماره همراه…'"
            />
          </div>

          <!-- Results dropdown -->
          <div class="sd-results" *ngIf="users.length > 0">
            <div
              class="sd-result-item"
              *ngFor="let user of users"
              [class.active]="selectedUser?.id === user.id"
              (click)="selectUser(user)"
            >
              <div class="result-avatar">{{ user.name?.[0]?.toUpperCase() }}</div>
              <div class="result-info">
                <span class="result-name">{{ user.name }}</span>
                <span class="result-mobile">{{ user.mobile }}</span>
              </div>
              <svg *ngIf="selectedUser?.id === user.id" class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
          </div>

          <!-- Selected user chip -->
          <div class="sd-selected-chip" *ngIf="selectedUser">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>{{ selectedUser.name }}</span>
            <button type="button" class="chip-remove" (click)="clearUser()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <p class="sd-error" *ngIf="submitted && !selectedUser">
            {{ getTranslation('userRequired') || 'انتخاب کاربر الزامی است' }}
          </p>
        </ng-container>

        <!-- Edit mode: static name -->
        <ng-container *ngIf="mode === 'edit'">
          <div class="sd-field-label">{{ getTranslation('name') }}</div>
          <div class="sd-static-field">
            <div class="result-avatar">{{ data.staff?.user?.name?.[0]?.toUpperCase() }}</div>
            <span>{{ data.staff?.user?.name }}</span>
          </div>
        </ng-container>

        <!-- Role -->
        <div class="sd-field-label">{{ getTranslation('role') }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <mat-select formControlName="role" [placeholder]="getTranslation('role')">
            <mat-option value="admin">Admin</mat-option>
            <mat-option value="manager">Manager</mat-option>
            <mat-option value="staff">Staff</mat-option>
          </mat-select>
          <mat-error *ngIf="staffForm.get('role')?.hasError('required')">
            {{ getTranslation('roleRequired') || 'نقش الزامی است' }}
          </mat-error>
        </mat-form-field>

        <!-- Expertise -->
        <div class="sd-field-label">{{ getTranslation('expertise') }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <mat-select formControlName="expertise_id" [placeholder]="getTranslation('expertise')">
            <mat-option *ngFor="let exp of expertises" [value]="exp.id">
              {{ exp.title }}
            </mat-option>
          </mat-select>
          <mat-error *ngIf="staffForm.get('expertise_id')?.hasError('required')">
            {{ getTranslation('expertiseRequired') || 'تخصص الزامی است' }}
          </mat-error>
        </mat-form-field>

        <!-- Actions -->
        <div class="sd-actions">
          <button class="sd-btn sd-btn-cancel" type="button" (click)="onCancel()">
            {{ getTranslation('cancel') }}
          </button>
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
    .sd {
      background: var(--bg-secondary);
      color: var(--text-primary);
      // width: 460px;
      max-width: 100%;
      display: flex;
      flex-direction: column;
    }

    .sd-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px 16px;
      border-bottom: 1px solid var(--border-color);
    }

    .sd-title-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .sd-accent-bar {
      display: block;
      width: 4px;
      height: 22px;
      background: var(--accent-color);
      border-radius: 3px;
      flex-shrink: 0;
    }

    .sd-title {
      font-size: 1rem;
      font-weight: 800;
      margin: 0;
      letter-spacing: -0.02em;
    }

    .sd-close-btn {
      width: 32px;
      height: 32px;
      border: none;
      background: transparent;
      cursor: pointer;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-secondary);
      transition: background 0.15s, color 0.15s;
    }
    .sd-close-btn svg { width: 16px; height: 16px; }
    .sd-close-btn:hover { background: var(--hover-bg); color: var(--text-primary); }

    .sd-form {
      padding: 20px 24px 24px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sd-field-label {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-secondary);
      margin-bottom: 6px;
      margin-top: 14px;
    }
    .sd-field-label:first-child { margin-top: 0; }

    .sd-search-box {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 0 12px;
      transition: border-color 0.15s;
    }
    .sd-search-box:focus-within { border-color: var(--accent-color); }
    .sd-search-box.has-results { border-radius: 10px 10px 0 0; }

    .search-icon { width: 16px; height: 16px; color: var(--text-secondary); flex-shrink: 0; }

    .sd-input {
      flex: 1;
      height: 42px;
      border: none;
      background: transparent;
      color: var(--text-primary);
      font-size: 0.875rem;
      outline: none;
    }
    .sd-input::placeholder { color: var(--text-secondary); opacity: 0.6; }

    .sd-results {
      border: 1px solid var(--accent-color);
      border-top: none;
      border-radius: 0 0 10px 10px;
      overflow: hidden;
      max-height: 200px;
      overflow-y: auto;
      scrollbar-width: thin;
      scrollbar-color: var(--border-color) transparent;
    }

    .sd-result-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      cursor: pointer;
      border-bottom: 1px solid var(--border-color);
      transition: background 0.12s;
      background: var(--bg-secondary);
    }
    .sd-result-item:last-child { border-bottom: none; }
    .sd-result-item:hover { background: var(--hover-bg); }
    .sd-result-item.active { background: var(--active-bg); }

    .result-avatar {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: var(--active-bg);
      color: var(--accent-color);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
      font-weight: 800;
      flex-shrink: 0;
    }

    .result-info { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .result-name { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
    .result-mobile { font-size: 0.72rem; color: var(--text-secondary); margin-top: 1px; }
    .check-icon { width: 16px; height: 16px; color: var(--accent-color); flex-shrink: 0; }

    .sd-selected-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--active-bg);
      border: 1px solid var(--border-color);
      border-radius: 20px;
      padding: 5px 10px 5px 8px;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--accent-color);
      margin-top: 8px;
      align-self: flex-start;
    }
    .sd-selected-chip svg { width: 14px; height: 14px; flex-shrink: 0; }

    .chip-remove {
      width: 18px;
      height: 18px;
      border: none;
      background: transparent;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      color: var(--text-secondary);
      padding: 0;
      transition: background 0.12s;
    }
    .chip-remove svg { width: 11px; height: 11px; }
    .chip-remove:hover { background: rgba(220,38,38,0.1); color: #dc2626; }

    .sd-static-field {
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-secondary);
    }

    .sd-mat-field {
      width: 100%;
    }
    .sd-mat-field ::ng-deep .mat-mdc-text-field-wrapper {
      background: var(--bg-primary) !important;
      border-radius: 10px !important;
    }
    .sd-mat-field ::ng-deep .mdc-notched-outline__leading,
    .sd-mat-field ::ng-deep .mdc-notched-outline__notch,
    .sd-mat-field ::ng-deep .mdc-notched-outline__trailing {
      border-color: var(--border-color) !important;
    }
    .sd-mat-field ::ng-deep .mat-mdc-select-value-text,
    .sd-mat-field ::ng-deep .mat-mdc-select-placeholder {
      color: var(--text-primary) !important;
      font-size: 0.875rem;
    }
    .sd-mat-field ::ng-deep .mat-mdc-floating-label {
      color: var(--text-secondary) !important;
    }

    .sd-error { font-size: 0.72rem; color: #dc2626; margin: 4px 0 0; }

    .sd-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--border-color);
    }

    .sd-btn {
      height: 38px;
      border-radius: 9px;
      border: none;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 700;
      padding: 0 18px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: opacity 0.15s, background 0.15s;
    }
    .sd-btn svg { width: 15px; height: 15px; }
    .sd-btn:disabled { opacity: 0.45; cursor: not-allowed; }

    .sd-btn-cancel {
      background: var(--bg-primary);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
    }
    .sd-btn-cancel:hover { background: var(--hover-bg); color: var(--text-primary); }

    .sd-btn-save { background: var(--accent-color); color: #fff; }
    .sd-btn-save:hover { opacity: 0.88; }
  `],
})
export class StaffDialogComponent implements OnInit {
  staffForm: FormGroup;
  searchControl = new FormControl('');
  users: any[] = [];
  selectedUser: any = null;
  expertises: any[] = [];
  mode: 'add' | 'edit' = 'add';
  submitted = false;

  private fb = inject(FormBuilder);
  private authHttp = inject(AuthHTTPService);
  private panelHttp = inject(PanelHttpService);
  public translationService = inject(TranslationService);

  constructor(
    public dialogRef: MatDialogRef<StaffDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: StaffDialogData
  ) {
    this.mode = data.mode;
    this.staffForm = this.fb.group({
      role: ['', Validators.required],
      expertise_id: ['', Validators.required],
      user_id: [null],
    });

    if (this.mode === 'edit' && data.staff) {
      this.staffForm.patchValue({
        role: data.staff.role,
        expertise_id: data.staff.expertise_id,
        user_id: data.staff.user_id,
      });
      this.selectedUser = data.staff.user;
    }
  }

  ngOnInit(): void {
    this.loadExpertises();
    this.setupUserSearch();
  }

  loadExpertises() {
    this.panelHttp.getExpertiseList({ is_paginate: false }).subscribe((res: any) => {
      if (res.success) this.expertises = res.data;
    });
  }

  setupUserSearch() {
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(value => {
        if (!value || value.length < 2) { this.users = []; return []; }
        return this.authHttp.listUsers({ name: value, is_paginate: true, count_item: 10 });
      })
    ).subscribe((res: any) => {
      if (res?.success) this.users = res.data.data || [];
    });
  }

  selectUser(user: any) {
    this.selectedUser = user;
    this.staffForm.patchValue({ user_id: user.id });
    this.users = [];
    this.searchControl.setValue('', { emitEvent: false });
  }

  clearUser() {
    this.selectedUser = null;
    this.staffForm.patchValue({ user_id: null });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onSubmit(): void {
    this.submitted = true;
    if (this.staffForm.valid && (this.mode === 'edit' || this.selectedUser)) {
      this.dialogRef.close({ mode: this.mode, data: this.staffForm.value });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
