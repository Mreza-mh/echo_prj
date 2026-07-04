import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { PanelHttpService } from '../panel-http.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { PanelService } from '../panel.service';
import { filter } from 'rxjs';
import { StaffScheduleDialogComponent } from './dialogs/staff-schedule-dialog.component';

@Component({
  selector: 'app-staff-schedule',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatSnackBarModule,
    MatDialogModule,
  ],
  templateUrl: './staff-schedule.html',
  styleUrl: './staff-schedule.scss',
})
export class StaffScheduleComponent implements OnInit {
  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['staff_name', 'day', 'start_time', 'end_time', 'actions'];

  ngOnInit() {
    this.loadSchedules();
  }
  data: any;
  loadSchedules() {
    this.panelHttp.getScheduleList({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.data = response;
          const flattenedData: any[] = [];

          response.data.forEach((record: any) => {
            if (record.schedule && Array.isArray(record.schedule)) {
              record.schedule.forEach((daySchedule: any) => {
                if (daySchedule.slots && Array.isArray(daySchedule.slots)) {
                  daySchedule.slots.forEach((slot: any) => {
                    flattenedData.push({
                      day: daySchedule.day,
                      start_time: slot.start,
                      end_time: slot.end,
                      id: record.id,
                      name: record.name,
                      expertise_name: record.expertise_name,
                      user_id: record.user_id,
                      expertise_id: record.expertise_id,
                      user: record.user,
                      expertise: record.expertise,
                      schedule_id: record.id,
                    });
                  });
                } else if (daySchedule.day) {
                  flattenedData.push({
                    day: daySchedule.day,
                    start_time: daySchedule.start_time,
                    end_time: daySchedule.end_time,
                    id: record.id,
                    name: record.name,
                    expertise_name: record.expertise_name,
                    user_id: record.user_id,
                    expertise_id: record.expertise_id,
                    user: record.user,
                    expertise: record.expertise,
                    schedule_id: record.id,
                  });
                }
              });
            }
          });

          this.dataSource.data = flattenedData;
          console.log('Flattened data:', flattenedData); // For debugging
        }
      },
      error: () => {
        this.snackBar.open(this.getTranslation('failedToLoadSchedules'), 'Close', {
          duration: 3000,
        });
      },
    });
  }

  getDayName(day: string): string {
    const days: any = {
      sat: this.getTranslation('sat') || 'شنبه',
      sun: this.getTranslation('sun') || 'یکشنبه',
      mon: this.getTranslation('mon') || 'دوشنبه',
      tue: this.getTranslation('tue') || 'سه‌شنبه',
      wed: this.getTranslation('wed') || 'چهارشنبه',
      thu: this.getTranslation('thu') || 'پنج‌شنبه',
      fri: this.getTranslation('fri') || 'جمعه',
    };
    return days[day] || day;
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  deleteSchedule(schedule: any) {
    const id = schedule.parentRecord ? schedule.parentRecord.id : schedule.id;
    if (
      confirm(
        this.getTranslation('confirmDeleteSchedule') ||
          'Are you sure you want to delete this schedule?',
      )
    ) {
      this.panelHttp.deleteSchedule(id).subscribe({
        next: (response: any) => {
          if (response.success) {
            this.snackBar.open(
              this.getTranslation('scheduleDeletedSuccessfully') || 'Schedule deleted successfully',
              'Close',
              { duration: 3000 },
            );
            this.loadSchedules();
          }
        },
      });
    }
  }

  openAddDialog() {
    const dialogRef = this.dialog.open(StaffScheduleDialogComponent, {
      width: '650px',
      data: { mode: 'add' },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        const { staff_id, ...scheduleData } = result.data;

        this.panelHttp.addSchedule(result.data.staff_id, scheduleData).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(
                this.getTranslation('scheduleAddedSuccessfully') || 'Schedule added successfully',
                'Close',
                { duration: 3000 },
              );
              this.loadSchedules();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error adding schedule', 'Close', {
              duration: 3000,
            });
          },
        });
      }
    });
  }

  openEditDialog(schedule: any) {
    const dialogRef = this.dialog.open(StaffScheduleDialogComponent, {
      width: '650px',
      data: { mode: 'edit', schedule: schedule.parentRecord || schedule },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        const id = schedule.parentRecord ? schedule.parentRecord.id : schedule.id;
        this.panelHttp.editSchedule(id, result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(
                this.getTranslation('scheduleUpdatedSuccessfully') ||
                  'Schedule updated successfully',
                'Close',
                { duration: 3000 },
              );
              this.loadSchedules();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error updating schedule', 'Close', {
              duration: 3000,
            });
          },
        });
      }
    });
  }
}
