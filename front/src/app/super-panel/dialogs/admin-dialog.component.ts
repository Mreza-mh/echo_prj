import { Component, Inject, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { debounceTime, distinctUntilChanged, switchMap, finalize } from 'rxjs/operators';
import { AuthHTTPService } from '../../auth/auth-http.service';
import { Organization } from '../models/organization.model';
import { TranslationService } from '../../@shared/services/translation.service';

@Component({
  selector: 'app-admin-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatListModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="admin-dialog-container" [dir]="getDirection()">
      <div class="dialog-header">
        <h2 mat-dialog-title>
          <mat-icon>person_add</mat-icon>
          <span>{{ getTranslation('addAdmin') }}</span>
        </h2>
        <div class="org-badge">{{ data.organization.name }}</div>
      </div>

      <div mat-dialog-content>
        <div class="search-wrapper">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ getTranslation('searchUser') }}</mat-label>
            <input
              matInput
              [formControl]="searchControl"
              [placeholder]="getTranslation('searchUserPlaceholder')"
              #searchInput
            />
            <mat-icon matPrefix color="primary">search</mat-icon>
            <button *ngIf="searchControl.value" matSuffix mat-icon-button (click)="searchControl.setValue('')">
              <mat-icon>close</mat-icon>
            </button>
          </mat-form-field>
        </div>

        <div class="user-list-results">
          <div *ngIf="isLoading" class="loading-state">
            <mat-spinner diameter="40"></mat-spinner>
            <p>{{ getTranslation('searching') }}</p>
          </div>

          <mat-selection-list [multiple]="false" (selectionChange)="onUserSelected($event)" class="custom-user-list">
            <mat-list-option *ngFor="let user of users" [value]="user" class="user-option">
              <div class="user-item">
                <div class="user-avatar">
                  <mat-icon>account_circle</mat-icon>
                </div>
                <div class="user-info">
                  <div class="user-name">{{ user.name }}</div>
                  <div class="user-mobile">{{ user.mobile }}</div>
                </div>
                <div class="user-action-hint">
                  <mat-icon color="primary">add_circle_outline</mat-icon>
                </div>
              </div>
            </mat-list-option>
          </mat-selection-list>

          <div *ngIf="!isLoading && users.length === 0 && searchControl.value" class="empty-state">
            <mat-icon>search_off</mat-icon>
            <p>{{ getTranslation('userNotFound') }}</p>
          </div>

          <div *ngIf="!isLoading && !searchControl.value" class="initial-state">
            <mat-icon>manage_search</mat-icon>
            <p>{{ getTranslation('searchUserPlaceholder') }}</p>
          </div>
        </div>
      </div>

      <div mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()" class="cancel-btn">{{ getTranslation('cancel') }}</button>
      </div>
    </div>
  `,
  styles: [
    `
      .admin-dialog-container {
        padding: 8px;
        min-width: 450px;
        max-width: 500px;
      }

      .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding: 0 16px;
        gap: 16px;

        h2 {
          margin: 0;
          display: flex;
          align-items: center;
          gap: 12px;
          color: var(--mat-sys-primary);
          font-weight: 600;
          font-size: 1.25rem;
          white-space: nowrap;

          mat-icon {
            margin: 0;
          }
        }

        .org-badge {
          background: var(--mat-sys-primary-container);
          color: var(--mat-sys-on-primary-container);
          padding: 4px 12px;
          border-radius: 16px;
          font-size: 0.8rem;
          font-weight: 600;
        }
      }

      .search-wrapper {
        margin-bottom: 8px;
      }

      .full-width {
        width: 100%;
      }

      mat-form-field {
        text-align: start;
      }

      .user-list-results {
        min-height: 280px;
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid var(--mat-sys-outline-variant);
        border-radius: 12px;
        background: var(--mat-sys-surface-container-low);
      }

      .loading-state,
      .empty-state,
      .initial-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 24px;
        color: var(--mat-sys-on-surface-variant);
        text-align: center;

        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
          margin-bottom: 16px;
          opacity: 0.6;
        }

        p {
          margin: 0;
          font-weight: 500;
          font-size: 0.9rem;
        }
      }

      .custom-user-list {
        padding: 0;
      }

      .user-option {
        border-bottom: 1px solid var(--mat-sys-outline-variant);
        height: auto !important;
        padding: 4px 0;

        &:last-child {
          border-bottom: none;
        }

        &:hover {
          background: var(--mat-sys-surface-container-high) !important;
        }
      }

      .user-item {
        display: flex;
        align-items: center;
        width: 100%;
        gap: 16px;
      }

      .user-avatar {
        width: 40px;
        height: 40px;
        background: var(--mat-sys-primary-container);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--mat-sys-on-primary-container);

        mat-icon {
          font-size: 24px;
          width: 24px;
          height: 24px;
        }
      }

      .user-info {
        flex: 1;
        text-align: start;

        .user-name {
          font-weight: 600;
          color: var(--mat-sys-on-surface);
          font-size: 0.95rem;
          margin-bottom: 2px;
        }

        .user-mobile {
          font-size: 0.85rem;
          color: var(--mat-sys-on-surface-variant);
          font-family: monospace;
          letter-spacing: 0.5px;
        }
      }

      .user-action-hint {
        opacity: 0.4;
        transition: all 0.2s ease-in-out;
      }

      .user-option:hover .user-action-hint {
        opacity: 1;
        transform: scale(1.15);
      }

      .cancel-btn {
        color: var(--mat-sys-on-surface-variant);
      }

      ::ng-deep {
        [dir='rtl'] {
          .dialog-header h2 mat-icon {
            margin-left: 0;
            margin-right: 0;
          }
          .user-item {
            gap: 16px;
          }
        }

        .mat-list-option .mat-list-item-content {
          padding: 0 16px !important;
        }
      }
    `,
  ],
})
export class AdminDialogComponent implements OnInit {
  public dialogRef = inject(MatDialogRef<AdminDialogComponent>);
  public data = inject<{ organization: Organization }>(MAT_DIALOG_DATA);
  private authService = inject(AuthHTTPService);
  private translationService = inject(TranslationService);

  searchControl = new FormControl('');
  users: any[] = [];
  selectedUser: any = null;
  isLoading = false;

  ngOnInit(): void {
    this.searchControl.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((value) => {
          if (!value) {
            this.users = [];
            return [];
          }
          this.isLoading = true;
          return this.authService
            .listUsers({
              name: value,
              is_paginate: true,
              count_item: 20,
            })
            .pipe(finalize(() => (this.isLoading = false)));
        })
      )
      .subscribe({
        next: (response) => {
          if (response && response.success && response.data) {
            this.users = response.data.data || [];
          } else {
            this.users = [];
          }
        },
        error: (error) => {
          console.error('Error fetching users', error);
          this.users = [];
        },
      });
  }

  onUserSelected(event: any): void {
    const selected = event.options[0]?.value;
    if (selected) {
      this.selectedUser = selected;
      this.dialogRef.close(this.selectedUser);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  getDirection(): 'ltr' | 'rtl' {
    return this.translationService.getDirection();
  }
}
