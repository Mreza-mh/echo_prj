import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { AuthHTTPService } from '../../auth/auth-http.service';
import { TranslationService } from '../../@shared/services/translation.service';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    MatSnackBarModule,
    ReactiveFormsModule
  ],
  template: `
    <div class="users-container">
      <div class="table-container">
        <div class="table-header">
          <div class="header-main">
            <h2>{{ getTranslation('users') }}</h2>
            <div class="search-box">
              <mat-form-field appearance="outline" class="search-field">
                <mat-icon matPrefix>search</mat-icon>
                <mat-label>{{ getTranslation('searchByMobile') || 'جستجو با موبایل' }}</mat-label>
                <input matInput [formControl]="searchControl" placeholder="0912...">
                <button *ngIf="searchControl.value" matSuffix mat-icon-button (click)="searchControl.setValue('')">
                  <mat-icon>close</mat-icon>
                </button>
              </mat-form-field>
            </div>
          </div>
          <div class="table-actions">
            <button mat-icon-button (click)="loadUsers()" [matTooltip]="getTranslation('refresh')">
              <mat-icon>refresh</mat-icon>
            </button>
          </div>
        </div>

        <mat-table [dataSource]="dataSource" class="users-table">
          <ng-container matColumnDef="id">
            <mat-header-cell *matHeaderCellDef>{{ getTranslation('id') }}</mat-header-cell>
            <mat-cell *matCellDef="let user">
              {{ user.id }}
            </mat-cell>
          </ng-container>

          <ng-container matColumnDef="name">
            <mat-header-cell *matHeaderCellDef>{{ getTranslation('name') }}</mat-header-cell>
            <mat-cell *matCellDef="let user">{{ user.name || '---' }}</mat-cell>
          </ng-container>

          <ng-container matColumnDef="mobile">
            <mat-header-cell *matHeaderCellDef>{{ getTranslation('mobile') }}</mat-header-cell>
            <mat-cell *matCellDef="let user">{{ user.mobile }}</mat-cell>
          </ng-container>

          <ng-container matColumnDef="role">
            <mat-header-cell *matHeaderCellDef>{{ getTranslation('role') }}</mat-header-cell>
            <mat-cell *matCellDef="let user">
              <span class="role-badge" [class.super-admin]="user.role === 'super_admin'">
                {{ user.role }}
              </span>
            </mat-cell>
          </ng-container>

          <ng-container matColumnDef="actions">
            <mat-header-cell *matHeaderCellDef>{{ getTranslation('actions') }}</mat-header-cell>
            <mat-cell *matCellDef="let user">
              <button mat-icon-button color="primary" [matTooltip]="getTranslation('edit')">
                <mat-icon>edit</mat-icon>
              </button>
            </mat-cell>
          </ng-container>

          <mat-header-row *matHeaderRowDef="displayedColumns"></mat-header-row>
          <mat-row *matRowDef="let row; columns: displayedColumns"></mat-row>
        </mat-table>

        <div class="empty-state" *ngIf="dataSource.data.length === 0">
          {{ getTranslation('noDataFound') || 'داده‌ای یافت نشد' }}
        </div>
      </div>
    </div>
  `,
  styles: [`
    .users-container {
      padding: 0;
    }
    .table-container {
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      box-shadow: 0 4px 20px var(--shadow);
      padding: 24px;
      overflow-x: auto;
      @media (max-width: 768px) {
        padding: 12px;
        margin: 8px;
      }

      .table-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        gap: 16px;

        .header-main {
          display: flex;
          align-items: center;
          gap: 24px;
          @media (max-width: 768px) {
            flex-direction: column;
            align-items: stretch;
            gap: 12px;
          }

          h2 {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
          }
        }

        .search-box {
          .search-field {
            width: 300px;
            --mdc-outlined-textField-container-shape: 28px;
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
            .mat-mdc-form-field-subscript-wrapper { display: none; }
            @media (max-width: 768px) {
              width: 100%;
            }
          }
        }

        .table-actions {
          @media (max-width: 768px) {
            display: flex;
            justify-content: flex-end;
          }
        }
      }

      mat-table {
        background: transparent;
        width: 100%;
        min-width: 450px;

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

      .role-badge {
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 500;
        background: var(--bg-secondary);
        color: var(--text-secondary);
        border: 1px solid var(--border-color);

        &.super-admin {
          background: var(--active-bg);
          color: var(--accent-color);
          border-color: var(--accent-color);
        }
      }

      .empty-state {
        text-align: center;
        padding: 48px;
        color: var(--text-secondary);
        font-size: 1.1rem;
      }
    }
  `]
})
export class UsersComponent implements OnInit {
  private authHttp = inject(AuthHTTPService);
  private translationService = inject(TranslationService);
  private snackBar = inject(MatSnackBar);

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['id', 'name', 'mobile', 'role', 'actions'];
  searchControl = new FormControl('');

  ngOnInit() {
    this.loadUsers();

    this.searchControl.valueChanges.pipe(
      debounceTime(400),
      distinctUntilChanged()
    ).subscribe(value => {
      this.loadUsers(value || '');
    });
  }

  loadUsers(mobile: string = '') {
    this.authHttp.listUsers({ 
      mobile: mobile,
      is_paginate: false 
    }).subscribe({
      next: (response: any) => {
        if (response.success) {
          this.dataSource.data = response.data;
        }
      },
      error: (error) => {
        this.snackBar.open(this.getTranslation('failedToLoadUsers') || 'خطا در بارگذاری کاربران', 'Close', { duration: 3000 });
      }
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }
}
