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
import { Router } from '@angular/router';
import { MatTooltipModule } from '@angular/material/tooltip';
import { OrganizationServiceDialogComponent } from './dialogs/organization-service-dialog.component';

@Component({
  selector: 'app-organization-service',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTooltipModule
  ],
  templateUrl: './organization-service.html',
  styleUrl: './organization-service.scss',
})
export class OrganizationServiceComponent implements OnInit {
  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  private router = inject(Router);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['name', 'price', 'duration', 'actions'];

  ngOnInit() {
    this.loadServices();
  }

  loadServices() {
    this.panelHttp.getOrgServiceList({ is_paginate: false }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.dataSource.data = response.data;
        }
      },
      error: () => {
        this.snackBar.open(this.getTranslation('failedToLoadServices'), 'Close', { duration: 3000 });
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  goToAppointment(service: any) {
    this.router.navigate(['/panel/appointment'], {
      queryParams: {
        service_id: service.id,
      }
    });
  }

  deleteService(service: any) {
    if (confirm(this.getTranslation('confirmDeleteService') || 'Are you sure you want to delete this service?')) {
      this.panelHttp.deleteOrgService(service.id).subscribe({
        next: (response: any) => {
          if (response.success) {
            this.snackBar.open(this.getTranslation('serviceDeletedSuccessfully') || 'Service deleted successfully', 'Close', { duration: 3000 });
            this.loadServices();
          }
        }
      });
    }
  }

  openAddDialog() {
    const dialogRef = this.dialog.open(OrganizationServiceDialogComponent, {
      width: '500px',
      data: { mode: 'add' }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.addOrgService(result).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('serviceAddedSuccessfully') || 'Service added successfully', 'Close', { duration: 3000 });
              this.loadServices();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error adding service', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  openEditDialog(service: any) {
    const dialogRef = this.dialog.open(OrganizationServiceDialogComponent, {
      width: '500px',
      data: { mode: 'edit', orgService: service }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.panelHttp.editOrgService(service.id, result.data).subscribe({
          next: (res) => {
            if (res.success) {
              this.snackBar.open(this.getTranslation('serviceUpdatedSuccessfully') || 'Service updated successfully', 'Close', { duration: 3000 });
              this.loadServices();
            }
          },
          error: (err) => {
            this.snackBar.open(err.error?.message || 'Error updating service', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }
}
