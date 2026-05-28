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
import { ResourceDialogComponent } from './dialogs/resource-dialog.component';

@Component({
  selector: 'app-resource',
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
  templateUrl: './resource.html',
  styleUrl: './resource.scss',
})
export class ResourceComponent implements OnInit {
  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['name', 'type', 'actions'];

  ngOnInit() {
    this.loadResources();
  }

  loadResources() {
    this.panelHttp.getResourceList({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.dataSource.data = response.data;
        }
      },
      error: () => {
        this.snackBar.open(this.getTranslation('failedToLoadResources'), 'Close', { duration: 3000 });
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  deleteResource(resource: any) {
    if (confirm(this.getTranslation('confirmDeleteResource') || 'Are you sure you want to delete this resource?')) {
      this.panelHttp.deleteResource(resource.id).subscribe({
        next: (response: any) => {
          if (response.success) {
            this.snackBar.open(this.getTranslation('resourceDeletedSuccessfully') || 'Resource deleted successfully', 'Close', { duration: 3000 });
            this.loadResources();
          }
        }
      });
    }
  }

  openAddDialog() {
    const dialogRef = this.dialog.open(ResourceDialogComponent, {
      width: '500px',
      data: { mode: 'add' }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.addResource(result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('resourceAddedSuccessfully') || 'Resource added successfully', 'Close', { duration: 3000 });
              this.loadResources();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error adding resource', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  openEditDialog(resource: any) {
    const dialogRef = this.dialog.open(ResourceDialogComponent, {
      width: '500px',
      data: { mode: 'edit', resource: resource }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.editResource(resource.id, result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('resourceUpdatedSuccessfully') || 'Resource updated successfully', 'Close', { duration: 3000 });
              this.loadResources();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error updating resource', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }
}
