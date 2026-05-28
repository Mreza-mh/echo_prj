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
import { OrganizationService } from '../services/organization.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { Organization } from '../models/organization.model';
import { OrganizationDialogComponent } from '../dialogs/organization-dialog.component';
import { ConfirmDialogComponent } from '../dialogs/confirm-dialog.component';
import { AdminDialogComponent } from '../dialogs/admin-dialog.component';

@Component({
  selector: 'app-organizations',
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
          <h2>{{ getTranslation('organizations') }}</h2>
          <div class="search-box">
            <mat-form-field appearance="outline" class="search-field">
              <mat-icon matPrefix>search</mat-icon>
              <mat-label>{{ getTranslation('searchByName') }}</mat-label>
              <input matInput [formControl]="searchControl" [placeholder]="getTranslation('searchPlaceholder')">
              <button *ngIf="searchControl.value" matSuffix mat-icon-button (click)="searchControl.setValue('')">
                <mat-icon>close</mat-icon>
              </button>
            </mat-form-field>
          </div>
        </div>
        <div class="table-actions">
          <button mat-raised-button color="primary" (click)="openOrganizationDialog('add')">
            <mat-icon>add</mat-icon>
            {{ getTranslation('addOrganization') }}
          </button>
          <button mat-icon-button (click)="loadOrganizations()" [matTooltip]="getTranslation('refresh')">
            <mat-icon>refresh</mat-icon>
          </button>
        </div>
      </div>

      <mat-table [dataSource]="dataSource" class="organizations-table">
        <ng-container matColumnDef="id">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('id') }}</mat-header-cell>
          <mat-cell *matCellDef="let org">
            <span [matTooltip]="org.id">{{ org.id | slice:0:8 }}...</span>
          </mat-cell>
        </ng-container>

        <ng-container matColumnDef="name">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('name') }}</mat-header-cell>
          <mat-cell *matCellDef="let org">{{ org.name }}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="business_type">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('type') }}</mat-header-cell>
          <mat-cell *matCellDef="let org">{{ org.business_type }}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="phone">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('phone') }}</mat-header-cell>
          <mat-cell *matCellDef="let org">{{ org.phone }}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="address">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('address') }}</mat-header-cell>
          <mat-cell *matCellDef="let org">
            <span [matTooltip]="org.address" class="truncate-address">{{ org.address }}</span>
          </mat-cell>
        </ng-container>

        <ng-container matColumnDef="actions">
          <mat-header-cell *matHeaderCellDef>{{ getTranslation('actions') }}</mat-header-cell>
          <mat-cell *matCellDef="let org">
            <button mat-icon-button color="primary" (click)="openAdminDialog(org)" [matTooltip]="getTranslation('addAdmin')">
              <mat-icon>person_add</mat-icon>
            </button>
            <button mat-icon-button (click)="openOrganizationDialog('edit', org)" [matTooltip]="getTranslation('edit')">
              <mat-icon>edit</mat-icon>
            </button>
            <button mat-icon-button color="warn" (click)="deleteOrganization(org)" [matTooltip]="getTranslation('delete')">
              <mat-icon>delete</mat-icon>
            </button>
          </mat-cell>
        </ng-container>

        <mat-header-row *matHeaderRowDef="displayedColumns"></mat-header-row>
        <mat-row *matRowDef="let row; columns: displayedColumns;"></mat-row>
      </mat-table>
    </div>
  `,
  styles: [`
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
    .truncate-address {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 200px;
    }
    h2 {
      margin: 0;
      font-weight: 600;
      color: var(--text-primary);
    }
    .organizations-table {
      width: 100%;
      min-width: 650px;
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
  `]
})
  
export class OrganizationsComponent implements OnInit {
  private organizationService = inject(OrganizationService);
  private translationService = inject(TranslationService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private cdr = inject(ChangeDetectorRef);

  dataSource = new MatTableDataSource<Organization>([]);
  displayedColumns: string[] = ['id', 'name', 'business_type', 'phone', 'address', 'actions'];
  searchControl = new FormControl('');

  ngOnInit() {
    this.loadOrganizations();
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(query => this.loadOrganizations(query || ''));
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  loadOrganizations(name: string = '') {
    this.organizationService.getOrganizations({ name, is_paginate: false }).subscribe({
      next: (orgs) => {
        this.dataSource.data = Array.isArray(orgs) ? orgs : [];
        this.cdr.detectChanges();
      },
      error: (err) => this.snackBar.open(this.getTranslation('failedToLoadOrganizations'), 'Close', { duration: 3000 })
    });
  }

  openOrganizationDialog(mode: 'add' | 'edit', organization?: Organization) {
    const dialogRef = this.dialog.open(OrganizationDialogComponent, {
      width: '500px',
      data: { organization, mode }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (result.mode === 'add') {
          this.organizationService.createOrganization(result.data).subscribe({
            next: (org) => {
              this.loadOrganizations();
              this.openAdminDialog(org);
            },
            error: (err) => this.snackBar.open(this.getTranslation('failedToCreateOrganization'), 'Close', { duration: 3000 })
          });
        } else {
          this.organizationService.updateOrganization(organization!.id, result.data).subscribe({
            next: () => this.loadOrganizations(),
            error: (err) => this.snackBar.open(this.getTranslation('failedToUpdateOrganization'), 'Close', { duration: 3000 })
          });
        }
      }
    });
  }

  deleteOrganization(org: Organization) {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: this.getTranslation('deleteOrganization'),
        message: `${this.getTranslation('areYouSureYouWantToDelete')} "${org.name}"?`,
        confirmText: this.getTranslation('delete'),
        cancelText: this.getTranslation('cancel'),
        type: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirm => {
      if (confirm) {
        this.organizationService.deleteOrganization(org.id).subscribe({
          next: () => this.loadOrganizations(),
          error: (err) => this.snackBar.open(this.getTranslation('failedToDeleteOrganization'), 'Close', { duration: 3000 })
        });
      }
    });
  }

  openAdminDialog(organization: Organization) {
    const dialogRef = this.dialog.open(AdminDialogComponent, {
      width: '500px',
      data: { organization }
    });

    dialogRef.afterClosed().subscribe(user => {
      if (user) {
        this.organizationService.addAdmin( user.id).subscribe({
          next: () => this.snackBar.open(this.getTranslation('adminAddedSuccessfully'), 'Close', { duration: 3000 }),
          error: (err) => this.snackBar.open(this.getTranslation('failedToAddAdmin'), 'Close', { duration: 3000 })
        });
      }
    });
  }
}
