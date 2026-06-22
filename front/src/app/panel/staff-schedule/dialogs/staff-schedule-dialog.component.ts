import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormArray } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { PanelHttpService } from '../../panel-http.service';
import { TranslationService } from '../../../@shared/services/translation.service';

export interface StaffScheduleDialogData {
  schedule?: any;
  mode: 'add' | 'edit';
}

@Component({
  selector: 'app-staff-schedule-dialog',
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
  ],
  template: `
    <div class="sd" [dir]="translationService.getDirection()">

      <div class="sd-header">
        <div class="sd-title-row">
          <span class="sd-accent-bar"></span>
          <h2 class="sd-title">
            {{ mode === 'add' ? getTranslation('addSchedule') : getTranslation('editSchedule') }}
          </h2>
        </div>
        <button class="sd-close-btn" type="button" (click)="onCancel()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <form [formGroup]="scheduleForm" (ngSubmit)="onSubmit()" class="sd-form">

        <!-- Staff -->
        <div class="sd-field-label">{{ getTranslation('staff') || 'پرسنل' }}</div>
        <mat-form-field appearance="outline" class="sd-mat-field">
          <mat-select formControlName="staff_id">
            <mat-option *ngFor="let staff of staffList" [value]="staff.id">
              {{ staff.name || staff.user?.name || staff.id }}
              <span *ngIf="staff.expertise_name || staff.expertise?.title" style="font-size:0.8em;color:gray">
                ({{ staff.expertise_name || staff.expertise?.title }})
              </span>
            </mat-option>
          </mat-select>
          <mat-error *ngIf="scheduleForm.get('staff_id')?.hasError('required')">
            {{ getTranslation('staffRequired') || 'انتخاب پرسنل الزامی است' }}
          </mat-error>
        </mat-form-field>

        <!-- Slots header -->
        <div class="slots-head">
          <span class="sd-field-label" style="margin:0">{{ getTranslation('timeSlots') || 'بازه های زمانی' }}</span>
          <button class="add-slot-btn" type="button" (click)="addSlot()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
            {{ getTranslation('addTimeSlot') || 'افزودن بازه' }}
          </button>
        </div>

        <!-- Slots list -->
        <div formArrayName="schedule" class="slots-list">
          <div *ngFor="let slot of scheduleSlots.controls; let i=index"
               [formGroupName]="i" class="slot-card">
            <div class="slot-fields">
              <mat-form-field appearance="outline" class="sd-mat-field slot-field">
                <mat-label>{{ getTranslation('day') }}</mat-label>
                <mat-select formControlName="day">
                  <mat-option value="sat">{{ getTranslation('sat') || 'شنبه' }}</mat-option>
                  <mat-option value="sun">{{ getTranslation('sun') || 'یکشنبه' }}</mat-option>
                  <mat-option value="mon">{{ getTranslation('mon') || 'دوشنبه' }}</mat-option>
                  <mat-option value="tue">{{ getTranslation('tue') || 'سه‌شنبه' }}</mat-option>
                  <mat-option value="wed">{{ getTranslation('wed') || 'چهارشنبه' }}</mat-option>
                  <mat-option value="thu">{{ getTranslation('thu') || 'پنج‌شنبه' }}</mat-option>
                  <mat-option value="fri">{{ getTranslation('fri') || 'جمعه' }}</mat-option>
                </mat-select>
              </mat-form-field>

              <mat-form-field appearance="outline" class="sd-mat-field slot-field">
                <mat-label>{{ getTranslation('startTime') }}</mat-label>
                <input matInput type="time" formControlName="start_time" />
              </mat-form-field>

              <mat-form-field appearance="outline" class="sd-mat-field slot-field">
                <mat-label>{{ getTranslation('endTime') }}</mat-label>
                <input matInput type="time" formControlName="end_time" />
              </mat-form-field>
            </div>

            <button *ngIf="scheduleSlots.length > 1"
                    class="remove-slot-btn" type="button" (click)="removeSlot(i)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                <path d="M10 11v6"/><path d="M14 11v6"/>
                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
              </svg>
            </button>
          </div>
        </div>

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

    .slots-head { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; margin-bottom: 8px; }
    .add-slot-btn { display: inline-flex; align-items: center; gap: 5px; height: 32px; padding: 0 12px; border: 1px solid var(--accent-color); border-radius: 8px; background: transparent; color: var(--accent-color); font-size: 0.78rem; font-weight: 700; cursor: pointer; transition: background 0.15s; svg { width: 14px; height: 14px; } &:hover { background: var(--active-bg); } }

    .slots-list { display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--border-color) transparent; }
    .slot-card { background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px; display: flex; align-items: flex-start; gap: 8px; }
    .slot-fields { display: flex; flex: 1; gap: 8px; @media (max-width: 560px) { flex-direction: column; } }
    .slot-field { flex: 1; }
    .remove-slot-btn { width: 30px; height: 30px; border: none; background: transparent; cursor: pointer; border-radius: 7px; display: flex; align-items: center; justify-content: center; color: #dc2626; flex-shrink: 0; margin-top: 8px; transition: background 0.15s; svg { width: 15px; height: 15px; } &:hover { background: rgba(220,38,38,.1); } }

    .sd-mat-field { width: 100%; }
    .sd-mat-field ::ng-deep .mat-mdc-text-field-wrapper { background: var(--bg-primary) !important; border-radius: 10px !important; }
    .sd-mat-field ::ng-deep .mdc-notched-outline__leading, .sd-mat-field ::ng-deep .mdc-notched-outline__notch, .sd-mat-field ::ng-deep .mdc-notched-outline__trailing { border-color: var(--border-color) !important; }
    .sd-mat-field ::ng-deep .mat-mdc-select-value-text, .sd-mat-field ::ng-deep .mat-mdc-select-placeholder { color: var(--text-primary) !important; font-size: 0.875rem; }
    .sd-mat-field ::ng-deep .mat-mdc-floating-label { color: var(--text-secondary) !important; }
    .slot-field ::ng-deep .mat-mdc-text-field-wrapper { background: var(--bg-secondary) !important; }

    .sd-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color); }
    .sd-btn { height: 38px; border-radius: 9px; border: none; cursor: pointer; font-size: 0.85rem; font-weight: 700; padding: 0 18px; display: inline-flex; align-items: center; gap: 6px; transition: opacity 0.15s, background 0.15s; svg { width: 15px; height: 15px; } &:disabled { opacity: 0.45; cursor: not-allowed; } }
    .sd-btn-cancel { background: var(--bg-primary); color: var(--text-secondary); border: 1px solid var(--border-color); &:hover { background: var(--hover-bg); color: var(--text-primary); } }
    .sd-btn-save { background: var(--accent-color); color: #fff; &:hover { opacity: 0.88; } }
  `],
})
export class StaffScheduleDialogComponent implements OnInit {
  scheduleForm: FormGroup;
  staffList: any[] = [];
  mode: 'add' | 'edit' = 'add';

  private fb = inject(FormBuilder);
  private panelHttp = inject(PanelHttpService);
  public translationService = inject(TranslationService);

  constructor(
    public dialogRef: MatDialogRef<StaffScheduleDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: StaffScheduleDialogData
  ) {
    this.mode = data.mode;
    this.scheduleForm = this.fb.group({
      staff_id: [null, Validators.required],
      schedule: this.fb.array([]),
    });

    if (this.mode === 'edit' && data.schedule) {
      this.scheduleForm.patchValue({ staff_id: data.schedule.staff_id });
      let slots = data.schedule.schedule;
      if (typeof slots === 'string') { try { slots = JSON.parse(slots); } catch (e) { slots = []; } }
      if (Array.isArray(slots)) { slots.forEach(slot => this.addSlot(slot)); }
      else if (slots) { this.addSlot(slots); }
    } else {
      this.addSlot();
    }
  }

  ngOnInit(): void { this.loadStaff(); }

  get scheduleSlots() { return this.scheduleForm.get('schedule') as FormArray; }

  addSlot(slot: any = null) {
    this.scheduleSlots.push(this.fb.group({
      day: [slot?.day || '', Validators.required],
      start_time: [slot?.start_time || '', Validators.required],
      end_time: [slot?.end_time || '', Validators.required],
    }));
  }

  removeSlot(index: number) {
    if (this.scheduleSlots.length > 1) this.scheduleSlots.removeAt(index);
  }

  loadStaff() {
    this.panelHttp.getStaffList({ is_paginate: false }).subscribe((res: any) => {
      if (res.success) this.staffList = res.data;
    });
  }

  getTranslation(key: string): string { return this.translationService.getTranslation(key); }

  onSubmit(): void {
    if (this.scheduleForm.valid) {
      const formValue = this.scheduleForm.value;
      if (Array.isArray(formValue.schedule)) {
        formValue.schedule = formValue.schedule.map((slot: any) => ({
          ...slot,
          start_time: this.formatTime(slot.start_time),
          end_time: this.formatTime(slot.end_time),
        }));
      }
      this.dialogRef.close({ mode: this.mode, data: formValue });
    }
  }

  private formatTime(time: string): string {
    if (!time) return '';
    if (time.split(':').length === 3) return time;
    if (time.split(':').length === 2) return `${time}:00`;
    return time;
  }

  onCancel(): void { this.dialogRef.close(); }
}
