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
    <div class="schedule-dialog" [dir]="translationService.getDirection()">
      <h2 mat-dialog-title>
        {{ mode === 'add' ? getTranslation('addSchedule') : getTranslation('editSchedule') }}
      </h2>

      <form [formGroup]="scheduleForm" (ngSubmit)="onSubmit()" class="dialog-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ getTranslation('staff') || 'پرسنل' }}</mat-label>
          <mat-select formControlName="staff_id">
            <mat-option *ngFor="let staff of staffList" [value]="staff.id">
              {{ staff.name || staff.user?.name || staff.id }}
              <span *ngIf="staff.expertise_name || staff.expertise?.title" style="font-size: 0.8em; color: gray;">
                ({{ staff.expertise_name || staff.expertise?.title }})
              </span>
            </mat-option>
          </mat-select>
          <mat-error *ngIf="scheduleForm.get('staff_id')?.hasError('required')">
            {{ getTranslation('staffRequired') || 'انتخاب پرسنل الزامی است' }}
          </mat-error>
        </mat-form-field>

        <div class="slots-header">
          <span class="slots-title">{{ getTranslation('timeSlots') || 'بازه های زمانی' }}</span>
          <button mat-stroked-button type="button" (click)="addSlot()" color="primary" class="add-slot-btn">
            <mat-icon>add</mat-icon>
            {{ getTranslation('addTimeSlot') || 'افزودن بازه زمانی' }}
          </button>
        </div>

        <div formArrayName="schedule" class="slots-container">
          <div *ngFor="let slot of scheduleSlots.controls; let i=index" [formGroupName]="i" class="slot-row">
            <mat-form-field appearance="outline">
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

            <mat-form-field appearance="outline">
              <mat-label>{{ getTranslation('startTime') }}</mat-label>
              <input matInput type="time" formControlName="start_time" />
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>{{ getTranslation('endTime') }}</mat-label>
              <input matInput type="time" formControlName="end_time" />
            </mat-form-field>

            <button mat-icon-button color="warn" type="button" (click)="removeSlot(i)" *ngIf="scheduleSlots.length > 1" class="remove-btn">
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </div>

        <div class="dialog-actions">
          <button mat-button type="button" (click)="onCancel()">{{ getTranslation('cancel') }}</button>
          <button
            mat-raised-button
            color="primary"
            type="submit"
            [disabled]="scheduleForm.invalid"
          >
            {{ getTranslation('save') }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .schedule-dialog {
        padding: 8px;
        min-width: 550px;
        @media (max-width: 768px) {
          min-width: unset;
          width: 100%;
        }
      }
      .dialog-form {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-top: 16px;
      }
      .full-width {
        width: 100%;
      }
      .slots-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        padding: 0 4px;
        @media (max-width: 768px) {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }
      }
      .slots-title {
        font-weight: 500;
        color: var(--text-secondary);
      }
      .slots-container {
        max-height: 350px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 12px;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        @media (max-width: 768px) {
          padding: 8px;
        }
      }
      .slot-row {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        padding: 12px;
        background: var(--bg-primary);
        border-radius: 8px;
        box-shadow: 0 2px 4px var(--shadow);
        @media (max-width: 768px) {
          flex-direction: column;
          gap: 8px;
          padding: 8px;
        }
      }
      .slot-row mat-form-field {
        flex: 1;
        @media (max-width: 768px) {
          width: 100%;
        }
      }
      .remove-btn {
        margin-top: 8px;
        @media (max-width: 768px) {
          align-self: flex-end;
          margin-top: 0;
        }
      }
      .add-slot-btn {
        margin-top: 8px;
        @media (max-width: 768px) {
          width: 100%;
          margin-top: 0;
        }
      }
      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 24px;
        padding-top: 16px;
        border-top: 1px solid var(--border-color);
      }
    `,
  ],
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
      this.scheduleForm.patchValue({
        staff_id: data.schedule.staff_id,
      });
      // Handle the case where schedule might be a string or object
      let slots = data.schedule.schedule;
      if (typeof slots === 'string') {
        try { slots = JSON.parse(slots); } catch (e) { slots = []; }
      }
      if (Array.isArray(slots)) {
        slots.forEach(slot => this.addSlot(slot));
      } else if (slots) {
        this.addSlot(slots);
      }
    } else {
      this.addSlot();
    }
  }

  ngOnInit(): void {
    this.loadStaff();
  }

  get scheduleSlots() {
    return this.scheduleForm.get('schedule') as FormArray;
  }

  addSlot(slot: any = null) {
    const slotGroup = this.fb.group({
      day: [slot?.day || '', Validators.required],
      start_time: [slot?.start_time || '', Validators.required],
      end_time: [slot?.end_time || '', Validators.required],
    });
    this.scheduleSlots.push(slotGroup);
  }

  removeSlot(index: number) {
    if (this.scheduleSlots.length > 1) {
      this.scheduleSlots.removeAt(index);
    }
  }

  loadStaff() {
    this.panelHttp.getStaffList({ is_paginate: false }).subscribe(res => {
      if (res.success) {
        this.staffList = res.data;
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onSubmit(): void {
    if (this.scheduleForm.valid) {
      const formValue = this.scheduleForm.value;
      
      // Ensure time format is HH:MM:SS
      if (formValue.schedule && Array.isArray(formValue.schedule)) {
        formValue.schedule = formValue.schedule.map((slot: any) => ({
          ...slot,
          start_time: this.formatTime(slot.start_time),
          end_time: this.formatTime(slot.end_time)
        }));
      }

      this.dialogRef.close({
        mode: this.mode,
        data: formValue,
      });
    }
  }

  private formatTime(time: string): string {
    if (!time) return '';
    // If it's already HH:MM:SS, return it
    if (time.split(':').length === 3) return time;
    // If it's HH:MM, append :00
    if (time.split(':').length === 2) return `${time}:00`;
    return time;
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
