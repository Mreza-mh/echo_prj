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
import { StatusDialogComponent } from './dialogs/status-dialog.component';

@Component({
  selector: 'app-status',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatSnackBarModule,
    MatDialogModule
  ],
  templateUrl: './status.html',
  styleUrl: './status.scss',
})
export class StatusComponent implements OnInit {
  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['title', 'label', 'actions'];

  ngOnInit() {

    this.loadStatuses();
  }

  loadStatuses() {
    this.panelHttp.getStatusList({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.dataSource.data = response.data;
        }
      },
      error: () => {
        this.snackBar.open(this.getTranslation('failedToLoadStatuses'), 'Close', { duration: 3000 });
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  deleteStatus(status: any) {
    if (confirm(this.getTranslation('confirmDeleteStatus') || 'Are you sure you want to delete this status?')) {
      this.panelHttp.deleteStatus(status.id).subscribe({
        next: (response: any) => {
          if (response.success) {
            this.snackBar.open(this.getTranslation('statusDeletedSuccessfully') || 'Status deleted successfully', 'Close', { duration: 3000 });
            this.loadStatuses();
          }
        }
      });
    }
  }

  openAddDialog() {
    const dialogRef = this.dialog.open(StatusDialogComponent, {
      width: '500px',
      data: { mode: 'add' }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.addStatus(result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('statusAddedSuccessfully') || 'Status added successfully', 'Close', { duration: 3000 });
              this.loadStatuses();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error adding status', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  openEditDialog(status: any) {
    const dialogRef = this.dialog.open(StatusDialogComponent, {
      width: '500px',
      data: { mode: 'edit', status }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.editStatus(status.id, result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('statusUpdatedSuccessfully') || 'Status updated successfully', 'Close', { duration: 3000 });
              this.loadStatuses();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error updating status', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }
}
