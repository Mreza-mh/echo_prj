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
import { debounceTime, distinctUntilChanged, switchMap, finalize } from 'rxjs';
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
    <div class="staff-dialog" [dir]="translationService.getDirection()">
      <h2 mat-dialog-title>
        {{ mode === 'add' ? getTranslation('addStaff') : getTranslation('editStaff') }}
      </h2>

      <form [formGroup]="staffForm" (ngSubmit)="onSubmit()" class="dialog-form">
        <!-- User Search (Only for Add mode) -->
        <div *ngIf="mode === 'add'" class="user-search-section">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('searchUser') || 'جستجوی کاربر' }}</mat-label>
            <input
              matInput
              [formControl]="searchControl"
              [placeholder]="getTranslation('searchUserPlaceholder') || 'نام یا شماره همراه را وارد کنید'"
            />
            <mat-icon matSuffix>search</mat-icon>
          </mat-form-field>

          <div class="user-results" *ngIf="users.length > 0">
            <mat-selection-list [multiple]="false" (selectionChange)="onUserSelected($event)">
              <mat-list-option *ngFor="let user of users" [value]="user" [selected]="selectedUser?.id === user.id">
                <div class="user-item">
                  <span class="user-name">{{ user.name }}</span>
                  <span class="user-mobile">{{ user.mobile }}</span>
                </div>
              </mat-list-option>
            </mat-selection-list>
          </div>
          
          <div class="selected-user-info" *ngIf="selectedUser">
            <mat-icon color="primary">check_circle</mat-icon>
            <span>{{ getTranslation('selectedUser') || 'کاربر انتخاب شده' }}: <b>{{ selectedUser.name }}</b></span>
          </div>
          <mat-error *ngIf="submitted && !selectedUser && mode === 'add'">
            {{ getTranslation('userRequired') || 'انتخاب کاربر الزامی است' }}
          </mat-error>
        </div>

        <!-- Static Name Display (For Edit mode) -->
        <mat-form-field appearance="outline" class="full-width" *ngIf="mode === 'edit'">
          <mat-label>{{ getTranslation('name') }}</mat-label>
          <input matInput [value]="data.staff?.user?.name" disabled />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('role') }}</mat-label>
          <mat-select formControlName="role">
            <mat-option value="admin">Admin</mat-option>
            <mat-option value="manager">Manager</mat-option>
            <mat-option value="staff">Staff</mat-option>
          </mat-select>
          <mat-error *ngIf="staffForm.get('role')?.hasError('required')">
            {{ getTranslation('roleRequired') || 'نقش الزامی است' }}
          </mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('expertise') }}</mat-label>
          <mat-select formControlName="expertise_id">
            <mat-option *ngFor="let exp of expertises" [value]="exp.id">
              {{ exp.title }}
            </mat-option>
          </mat-select>
          <mat-error *ngIf="staffForm.get('expertise_id')?.hasError('required')">
            {{ getTranslation('expertiseRequired') || 'تخصص الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="dialog-actions">
          <button mat-button type="button" (click)="onCancel()">{{ getTranslation('cancel') }}</button>
          <button
            mat-raised-button
            color="primary"
            type="submit"
            [disabled]="staffForm.invalid"
          >
            {{ getTranslation('save') }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .staff-dialog {
        padding: 20px;
        min-width: 400px;
        max-width: 500px;
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
      .user-search-section {
        margin-bottom: 8px;
        border: 1px solid #eee;
        padding: 12px;
        border-radius: 8px;
      }
      .user-results {
        max-height: 200px;
        overflow-y: auto;
        margin-bottom: 8px;
        border: 1px solid #f0f0f0;
        border-radius: 4px;
      }
      .user-item {
        display: flex;
        justify-content: space-between;
        width: 100%;
        font-size: 14px;
      }
      .selected-user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #2e7d32;
        margin-top: 8px;
      }
      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 20px;
      }
      .user-name { font-weight: 500; }
      .user-mobile { color: #666; }
    `,
  ],
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
        user_id: data.staff.user_id
      });
      this.selectedUser = data.staff.user;
    }
  }

  ngOnInit(): void {
    this.loadExpertises();
    this.setupUserSearch();
  }

  loadExpertises() {
    this.panelHttp.getExpertiseList({ is_paginate: false }).subscribe(res => {
      if (res.success) {
        this.expertises = res.data;
      }
    });
  }

  setupUserSearch() {
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(value => {
        if (!value || value.length < 2) {
          this.users = [];
          return [];
        }
        return this.authHttp.listUsers({ name: value, is_paginate: true, count_item: 10 });
      })
    ).subscribe(res => {
      if (res.success) {
        this.users = res.data.data || [];
      }
    });
  }

  onUserSelected(event: any) {
    this.selectedUser = event.options[0].value;
    this.staffForm.patchValue({ user_id: this.selectedUser.id });
    this.users = [];
    this.searchControl.setValue('', { emitEvent: false });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onSubmit(): void {
    this.submitted = true;
    if (this.staffForm.valid && (this.mode === 'edit' || this.selectedUser)) {
      this.dialogRef.close({
        mode: this.mode,
        data: this.staffForm.value,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
