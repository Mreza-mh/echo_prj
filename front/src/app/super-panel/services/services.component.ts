import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { ServiceManagementService } from '../services/service.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { Service } from '../models/service.model';
import { ServiceDialogComponent } from '../dialogs/service-dialog.component';
import { ConfirmDialogComponent } from '../dialogs/confirm-dialog.component';

@Component({
  selector: 'app-services',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
    MatDialogModule,
    ReactiveFormsModule,
  ],
  template: `
    <div class="table-container">
      <div class="table-header">
        <div class="header-main">
          <h2>{{ getTranslation('services') }}</h2>
          <div class="search-box">
            <mat-form-field appearance="outline" class="search-field">
              <mat-icon matPrefix>search</mat-icon>
              <mat-label>{{ getTranslation('searchByTitle') }}</mat-label>
              <input
                matInput
                [formControl]="searchControl"
                [placeholder]="getTranslation('searchPlaceholder')"
              />
              <button
                *ngIf="searchControl.value"
                matSuffix
                mat-icon-button
                (click)="searchControl.setValue('')"
              >
                <mat-icon>close</mat-icon>
              </button>
            </mat-form-field>
          </div>
        </div>
        <div class="table-actions">
          <button mat-raised-button color="primary" (click)="openServiceDialog('add')">
            <mat-icon>add</mat-icon>
            {{ getTranslation('addService') }}
          </button>
          <button mat-icon-button (click)="loadServices()" [matTooltip]="getTranslation('refresh')">
            <mat-icon>refresh</mat-icon>
          </button>
        </div>
      </div>

      <mat-table [dataSource]="dataSource" class="services-table">
        <ng-container matColumnDef="id">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('id') }}</mat-header-cell>
          <mat-cell *matCellDef="let service">{{ service.id }}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="title">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('title') }}</mat-header-cell>
          <mat-cell *matCellDef="let service">{{ service.title }}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="default_duration">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('duration') }}</mat-header-cell>
          <mat-cell *matCellDef="let service"
            >{{ service.default_duration }} {{ getTranslation('minutes') }}</mat-cell
          >
        </ng-container>

        <ng-container matColumnDef="general_price">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('price') }}</mat-header-cell>
          <mat-cell *matCellDef="let service">{{ service.general_price | number }}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="actions">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('actions') }}</mat-header-cell>
          <mat-cell *matCellDef="let service">
            <button
              mat-icon-button
              (click)="openServiceDialog('edit', service)"
              [matTooltip]="getTranslation('edit')"
            >
              <mat-icon>edit</mat-icon>
            </button>
            <button
              mat-icon-button
              color="warn"
              (click)="deleteService(service)"
              [matTooltip]="getTranslation('delete')"
            >
              <mat-icon>delete</mat-icon>
            </button>
          </mat-cell>
        </ng-container>

        <mat-header-row *matHeaderRowDef="displayedColumns"></mat-header-row>
        <mat-row *matRowDef="let row; columns: displayedColumns"></mat-row>
      </mat-table>
    </div>
  `,
  styles: [
    `
      .table-container {
        padding: 24px;
        background: var(--bg-primary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        margin: 16px;
        overflow-x: auto;
        box-shadow: 0 4px 20px var(--shadow);
        @media (max-width: 768px) {
          padding: 12px;
          margin: 8px;
        }
      }
      .table-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        gap: 16px;
        flex-wrap: wrap;
      }
      .header-main {
        display: flex;
        align-items: center;
        gap: 24px;
        flex: 1;
        @media (max-width: 768px) {
          flex-direction: column;
          align-items: stretch;
          gap: 12px;
        }
      }
      .search-box {
        flex: 1;
        max-width: 400px;
        @media (max-width: 768px) {
          max-width: 100%;
        }
      }
      .search-field {
        width: 100%;
        ::ng-deep {
          .mat-mdc-form-field-flex {
            background-color: var(--bg-secondary) !important;
          }
          .mat-mdc-form-field-input-control {
            color: var(--text-primary) !important;
          }
          .mat-mdc-floating-label {
            color: var(--text-secondary) !important;
          }
        }
      }
      .table-actions {
        display: flex;
        gap: 8px;
        @media (max-width: 768px) {
          justify-content: flex-end;
        }
      }
      h2 {
        margin: 0;
        font-weight: 600;
        color: var(--text-primary);
      }
      .services-table {
        width: 100%;
        min-width: 450px;
        background: transparent !important;

        ::ng-deep {
          .mat-mdc-header-row {
            background-color: var(--bg-secondary) !important;
            min-height: 56px;
          }
          .mat-mdc-header-cell {
            color: var(--text-primary) !important;
            font-weight: 600;
            font-size: 0.9rem;
            border-bottom: 1px solid var(--border-color) !important;
          }
          .mat-mdc-row {
            min-height: 52px;
            &:hover {
              background-color: var(--hover-bg) !important;
            }
          }
          .mat-mdc-cell {
            color: var(--text-secondary) !important;
            border-bottom: 1px solid var(--border-color) !important;
          }
        }
      }
    `,
  ],
})
export class ServicesComponent implements OnInit {
  private serviceService = inject(ServiceManagementService);
  private translationService = inject(TranslationService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private cdr = inject(ChangeDetectorRef);

  dataSource = new MatTableDataSource<Service>([]);
  displayedColumns: string[] = ['id', 'title', 'default_duration', 'general_price', 'actions'];
  searchControl = new FormControl('');

  ngOnInit() {
    this.loadServices();
    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((query) => this.loadServices(query || ''));
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  loadServices(title: string = '') {
    this.serviceService.getServices({ title, is_paginate: false }).subscribe({
      next: (response) => {
        if (response?.success) {
          this.dataSource.data = response.data || [];
        }
        this.cdr.detectChanges();
      },
      error: (err) =>
        this.snackBar.open(this.getTranslation('failedToLoadServices'), 'Close', {
          duration: 3000,
        }),
    });
  }

  openServiceDialog(mode: 'add' | 'edit', service?: Service) {
    const dialogRef = this.dialog.open(ServiceDialogComponent, {
      width: '600px',
      data: { service, mode },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        if (result.mode === 'add') {
          this.serviceService.createService(result.data).subscribe({
            next: () => this.loadServices(),
            error: (err) =>
              this.snackBar.open(this.getTranslation('failedToCreateService'), 'Close', {
                duration: 3000,
              }),
          });
        } else {
          this.serviceService.updateService(service!.id, result.data).subscribe({
            next: () => this.loadServices(),
            error: (err) =>
              this.snackBar.open(this.getTranslation('failedToUpdateService'), 'Close', {
                duration: 3000,
              }),
          });
        }
      }
    });
  }

  deleteService(service: Service) {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: this.getTranslation('deleteService'),
        message: `${this.getTranslation('areYouSureYouWantToDelete')} "${service.title}"?`,
        confirmText: this.getTranslation('delete'),
        cancelText: this.getTranslation('cancel'),
        type: 'warn',
      },
    });

    dialogRef.afterClosed().subscribe((confirm) => {
      if (confirm) {
        this.serviceService.deleteService(service.id).subscribe({
          next: () => this.loadServices(),
          error: (err) =>
            this.snackBar.open(this.getTranslation('failedToDeleteService'), 'Close', {
              duration: 3000,
            }),
        });
      }
    });
  }
}
