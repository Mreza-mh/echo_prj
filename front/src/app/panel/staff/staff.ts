import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { PanelHttpService } from '../panel-http.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { PanelService } from '../panel.service';
import { filter } from 'rxjs';
import { Router } from '@angular/router';
import { MatTooltipModule } from '@angular/material/tooltip';
import { StaffDialogComponent } from './dialogs/staff-dialog.component';

@Component({
  selector: 'app-staff',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  templateUrl: './staff.html',
  styleUrl: './staff.scss',
})
export class StaffComponent implements OnInit {
  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  private router = inject(Router);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['id', 'name', 'role', 'expertise', 'actions'];

  ngOnInit() {
    this.loadStaff();
  }

  loadStaff() {
    this.panelHttp.getStaffList({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.dataSource.data = response.data;
        }
      },
      error: (error) => {
        this.snackBar.open(this.getTranslation('failedToLoadStaff'), 'Close', { duration: 3000 });
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  goToAppointment(staff: any) {
    this.router.navigate(['/panel/appointment'], {
      queryParams: {
        staff_id: staff.id,
      }
    });
  }

  deleteStaff(staff: any) {
    if (confirm(this.getTranslation('confirmDeleteStaff') || 'Are you sure you want to delete this staff?')) {
      this.panelHttp.deleteStaff(staff.id).subscribe({
        next: (response: any) => {
          if (response.success) {
            this.snackBar.open(this.getTranslation('staffDeletedSuccessfully') || 'Staff deleted successfully', 'Close', { duration: 3000 });
            this.loadStaff();
          }
        }
      });
    }
  }

  openAddDialog() {
    const dialogRef = this.dialog.open(StaffDialogComponent, {
      width: '500px',
      data: { mode: 'add' }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.addStaff(result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('staffAddedSuccessfully') || 'Staff added successfully', 'Close', { duration: 3000 });
              this.loadStaff();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error adding staff', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  openEditDialog(staff: any) {
    const dialogRef = this.dialog.open(StaffDialogComponent, {
      width: '500px',
      data: { mode: 'edit', staff }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.editStaff(staff.id, result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('staffUpdatedSuccessfully') || 'Staff updated successfully', 'Close', { duration: 3000 });
              this.loadStaff();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error updating staff', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }
}
