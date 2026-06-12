import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatCardModule } from '@angular/material/card';
import { MatNativeDateModule } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { IndexHttpService } from '../index-http.service';
import { PanelHttpService } from '../../panel/panel-http.service';
import { AuthHTTPService } from '../../auth/auth-http.service';
import { CredentialsService } from '../../auth/credentials.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';

@Component({
  selector: 'app-appointment',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDatepickerModule,
    MatCardModule,
    MatNativeDateModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatFormFieldModule,
    RouterModule,
  ],
  templateUrl: './appointment.component.html',
  styleUrls: ['./appointment.component.scss'],
})
export class AppointmentComponent implements OnInit {
  private translationService = inject(TranslationService);

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  selectedDate: Date | null = new Date();
  availableSlots: any[] = [];
  selectedSlot: any = null;
  isLoadingSlots = false;
  isBooking = false;

  staffList: any[] = [];
  serviceList: any[] = [];
  userList: any[] = [];
  resourceList: any[] = [];
  isLoadingData = false;
  organizationDetails: any = null;

  // Selection models
  selectedUserId: string = '';
  selectedResourceIds: string[] = [];

  isEditMode = false;
  isUserMode = false;
  editingAppointmentId: string | number | null = null;

  // Placeholder IDs
  organizationServicesId = '';
  staffId = '';
  hasStaffParam = false;
  hasServiceParam = false;

  constructor(
    private indexHttpService: IndexHttpService,
    private panelHttpService: PanelHttpService,
    private authHttpService: AuthHTTPService,
    private credentialsService: CredentialsService,
    private toastService: ToastService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      const routeStaffId = params['staffid'];
      this.route.queryParams.subscribe((queryParams) => {
        this.staffId = queryParams['staff_id'] || routeStaffId || '';
        this.organizationServicesId = queryParams['service_id'] || '';

        if (queryParams['date']) {
          this.selectedDate = new Date(queryParams['date']);
        }
        if (queryParams['time']) {
          this.selectedSlot = {
            start_time: queryParams['time'],
            end_time: '',
          };
        }

        this.hasStaffParam = !!this.staffId;
        this.hasServiceParam = !!this.organizationServicesId;

        this.isUserMode = queryParams['mode'] === 'user' || !this.router.url.includes('/panel/');

        if (this.isUserMode) {
          this.fetchCurrentUser();
        }

        if (queryParams['edit_id']) {
          this.loadAppointmentForEdit(queryParams['edit_id']);
        } else {
          this.loadInitialData();
        }

        // Auto-fetch slots if we have the minimum required data
        if (this.selectedDate && (this.organizationServicesId || this.staffId)) {
          this.fetchSlots(this.selectedDate);
        }
      });
    });
  }

  onStaffChange() {
    this.selectedSlot = null;
    this.availableSlots = []; // اضافه شد: پاک کردن تایم‌های قبلی
    this.checkAndFetchSlots();
  }

  onServiceChange() {
    this.selectedSlot = null;
    this.availableSlots = []; // اضافه شد: پاک کردن تایم‌های قبلی
    this.checkAndFetchSlots();
  }

  onDateChange(date: Date | null): void {
    this.selectedDate = date;
    this.selectedSlot = null;
    this.availableSlots = []; // اضافه شد: پاک کردن تایم‌های قبلی

    if (date) {
      this.checkAndFetchSlots(); // تغییر کرد: به جای فراخوانی مستقیم fetchSlots از این متد استفاده میکنیم تا شرط ها رعایت شود
    }
  }

  fetchCurrentUser() {
    this.authHttpService.getMe().subscribe({
      next: (res: any) => {
        if (res && res.data && res.data.id) {
          this.selectedUserId = String(res.data.id);
        } else if (
          this.credentialsService.credentials?.id ||
          this.credentialsService.credentials?.user?.id
        ) {
          this.selectedUserId = String(
            this.credentialsService.credentials?.id ||
              this.credentialsService.credentials?.user?.id,
          );
        }
      },
      error: () => {
        // Fallback to credentials if getMe fails
        const currentId =
          this.credentialsService.credentials?.id || this.credentialsService.credentials?.user?.id;
        if (currentId) {
          this.selectedUserId = String(currentId);
        }
      },
    });
  }

  loadInitialData() {
    this.isLoadingData = true;

    const params = { is_paginate: false };

    this.panelHttpService.getStaffList(params).subscribe({
      next: (res) => {
        this.staffList = res.data || [];
        this.checkAndFetchSlots();
      },
    });

    // Load Services
    this.panelHttpService.getOrgServiceList(params).subscribe({
      next: (res) => {
        this.serviceList = res.data || [];
        this.checkAndFetchSlots();
      },
    });

    // Load Resources (for selection)
    this.panelHttpService.getResourceList(params).subscribe({
      next: (res: any) => {
        this.resourceList = res.data || [];
      },
    });

    // Load Users (for admin/clerk to select a customer)
    if (!this.isUserMode) {
      this.authHttpService.listUsers({ is_paginate: false }).subscribe({
        next: (res: any) => {
          this.userList = res.data || [];
          if (!this.isEditMode && !this.selectedUserId) {
            this.fetchCurrentUser();
          }
        },
        complete: () => {
          this.isLoadingData = false;
        },
      });
    } else {
      this.fetchCurrentUser();
      this.isLoadingData = false;
    }
  }

  checkAndFetchSlots() {
    if (this.selectedDate && (this.organizationServicesId || this.staffId)) {
      this.fetchSlots(this.selectedDate);
    }
  }



  fetchSlots(date: Date): void {
    if (!this.organizationServicesId && !this.staffId) return;

    this.isLoadingSlots = true;
    const formattedDate = this.formatDate(date);

    const params: any = {
      date: formattedDate,
    };

    if (this.organizationServicesId) params.service_id = String(this.organizationServicesId);
    if (this.staffId) params.staff_id = String(this.staffId);
    if (this.staffId) {
      this.indexHttpService.getAvailableSlots(params).subscribe({
        next: (res) => {
          this.availableSlots = res.data || [];

          if (this.isEditMode && this.selectedSlot) {
            const exists = this.availableSlots.find(
              (s) => s.start_time === this.selectedSlot.start_time,
            );
            if (!exists) {
              this.availableSlots.push(this.selectedSlot);
              this.availableSlots.sort((a, b) => a.start_time.localeCompare(b.start_time));
            }

            this.selectedSlot = this.availableSlots.find(
              (s) => s.start_time === this.selectedSlot.start_time,
            );
          }

          this.isLoadingSlots = false;
        },
        error: (err) => {
          this.toastService.error('خطا در دریافت زمان‌های خالی');
          this.isLoadingSlots = false;
        },
      });
    }
  }

  selectSlot(slot: any): void {
    this.selectedSlot = slot;
  }

  toggleResource(resourceId: string): void {
    const index = this.selectedResourceIds.indexOf(resourceId);
    if (index > -1) {
      this.selectedResourceIds.splice(index, 1);
    } else {
      this.selectedResourceIds.push(resourceId);
    }
  }

  bookAppointment(): void {
    if (!this.selectedSlot || !this.selectedDate) return;

    if (!this.selectedUserId) {
      this.toastService.error('لطفاً مشتری را انتخاب کنید');
      return;
    }

    this.isBooking = true;
    const bookingData = {
      user_id: this.selectedUserId,
      staff_id: this.staffId,
      service_id: this.organizationServicesId,
      date_of_turn: this.formatDate(this.selectedDate),
      start_time: this.selectedSlot.start_time,
      type: 'Online',
      permissible_interference: false,
      resource_ids: this.selectedResourceIds,
    };

    const request =
      this.isEditMode && this.editingAppointmentId
        ? this.panelHttpService.editAppointment(this.editingAppointmentId, bookingData)
        : this.indexHttpService.addAppointment(bookingData);

    request.subscribe({
      next: (res) => {
        this.toastService.success(
          this.isEditMode ? 'نوبت با موفقیت ویرایش شد' : 'نوبت شما با موفقیت ثبت شد',
        );
        this.isBooking = false;
        this.selectedSlot = null;
        if (this.isEditMode) {
          this.router.navigate(['/panel/dashboard']);
        } else {
          this.fetchSlots(this.selectedDate!);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'خطا در ثبت نوبت');
        this.isBooking = false;
      },
    });
  }

  loadAppointmentForEdit(id: string | number) {
    this.isEditMode = true;
    this.editingAppointmentId = id;
    this.panelHttpService.getAppointmentDetails(String(id)).subscribe({
      next: (res: any) => {
        const app = res.data;
        this.selectedDate = new Date(app.date_of_turn);
        this.staffId = String(app.staff_id);
        this.organizationServicesId = String(app.service_id);
        this.selectedUserId = String(app.user_id || app.user?.id || app.user || '');
        this.selectedResourceIds = app.resources ? app.resources.map((r: any) => String(r.id)) : [];

        this.loadInitialData();

        this.fetchSlots(this.selectedDate);

        if (app.start_time) {
          this.selectedSlot = {
            start_time: app.start_time.substring(0, 5),
            end_time: app.end_time ? app.end_time.substring(0, 5) : '',
          };
        }
      },
    });
  }

  private formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
}
