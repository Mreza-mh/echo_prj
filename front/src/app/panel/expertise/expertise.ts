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
import { ExpertiseDialogComponent } from './dialogs/expertise-dialog.component';

@Component({
  selector: 'app-expertise',
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
  templateUrl: './expertise.html',
  styleUrl: './expertise.scss',
})
export class ExpertiseComponent implements OnInit {
  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['title', 'label', 'actions'];

  ngOnInit() {
    this.loadExpertises();
  }

  loadExpertises() {
    this.panelHttp.getExpertiseList({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.dataSource.data = response.data;
        }
      },
      error: () => {
        this.snackBar.open(this.getTranslation('failedToLoadExpertises'), 'Close', { duration: 3000 });
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  deleteExpertise(expertise: any) {
    if (confirm(this.getTranslation('confirmDeleteExpertise') || 'Are you sure you want to delete this expertise?')) {
      this.panelHttp.deleteExpertise(expertise.id).subscribe({
        next: (response: any) => {
          if (response.success) {
            this.snackBar.open(this.getTranslation('expertiseDeletedSuccessfully') || 'Expertise deleted successfully', 'Close', { duration: 3000 });
            this.loadExpertises();
          }
        }
      });
    }
  }

  openAddDialog() {
    const dialogRef = this.dialog.open(ExpertiseDialogComponent, {
      width: '500px',
      data: { mode: 'add' }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.addExpertise(result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('expertiseAddedSuccessfully') || 'Expertise added successfully', 'Close', { duration: 3000 });
              this.loadExpertises();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error adding expertise', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  openEditDialog(expertise: any) {
    const dialogRef = this.dialog.open(ExpertiseDialogComponent, {
      width: '500px',
      data: { mode: 'edit', expertise }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.editExpertise(expertise.id, result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('expertiseUpdatedSuccessfully') || 'Expertise updated successfully', 'Close', { duration: 3000 });
              this.loadExpertises();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error updating expertise', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }
}
