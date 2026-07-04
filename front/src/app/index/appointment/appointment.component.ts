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
import { forkJoin } from 'rxjs';

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

  getDirection(): 'ltr' | 'rtl' {
    return this.translationService.getDirection();
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

  selectedUserId: string = '';
  selectedResourceIds: string[] = [];

  isEditMode = false;
  isUserMode = false;
  editingAppointmentId: string | number | null = null;

  organizationServicesId = '';
  staffId = '';
  hasStaffParam = false;
  hasServiceParam = false;

  // Time slot to restore after lists finish loading
  private pendingSlotTime: string | null = null;

  // مقدار query param رشته است ولی [value] گزینه‌ها عدد — مقایسه پیش‌فرض mat-select
  // سخت‌گیرانه است و select خالی می‌ماند؛ این مقایسه هر دو را هم‌نوع می‌کند
  compareIds = (a: unknown, b: unknown): boolean =>
    a != null && b != null && String(a) === String(b);

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

        this.isUserMode = queryParams['mode'] === 'user' || !this.router.url.includes('/panel/');

        if (queryParams['date']) {
          this.selectedDate = new Date(queryParams['date']);
        }

        if (queryParams['time']) {
          this.pendingSlotTime = queryParams['time'];
        }

        if (queryParams['edit_id']) {
          this.loadAppointmentForEdit(queryParams['edit_id']);
        } else {
          // Set params BEFORE loading lists so selects can match
          this.staffId               = queryParams['staff_id'] || routeStaffId || '';
          this.organizationServicesId = queryParams['service_id'] || '';
          this.hasStaffParam   = !!this.staffId;
          this.hasServiceParam = !!this.organizationServicesId;

          if (this.isUserMode) this.fetchCurrentUser();
          this.loadInitialData();
        }
      });
    });
  }

  onStaffChange() {
    this.selectedSlot = null;
    this.availableSlots = [];
    this.checkAndFetchSlots();
  }

  onServiceChange() {
    this.selectedSlot = null;
    this.availableSlots = [];
    this.checkAndFetchSlots();
  }

  onDateChange(date: Date | null): void {
    this.selectedDate = date;
    this.selectedSlot = null;
    this.availableSlots = [];
    if (date) this.checkAndFetchSlots();
  }

  fetchCurrentUser() {
    this.authHttpService.getMe().subscribe({
      next: (res: any) => {
        if (res?.data?.id) {
          this.selectedUserId = String(res.data.id);
        } else {
          const id = this.credentialsService.credentials?.id
            ?? this.credentialsService.credentials?.user?.id;
          if (id) this.selectedUserId = String(id);
        }
      },
      error: () => {
        const id = this.credentialsService.credentials?.id
          ?? this.credentialsService.credentials?.user?.id;
        if (id) this.selectedUserId = String(id);
      },
    });
  }

  loadInitialData() {
    this.isLoadingData = true;
    const params = { is_paginate: false };

    forkJoin({
      staff:    this.panelHttpService.getStaffList(params),
      service:  this.panelHttpService.getOrgServiceList(params),
      resource: this.panelHttpService.getResourceList(params),
    }).subscribe({
      next: ({ staff, service, resource }) => {
        this.staffList    = staff.data    || [];
        this.serviceList  = service.data  || [];
        this.resourceList = resource.data || [];

        // Normalize staffId to match the exact value used in mat-option
        // پارامتر URL ممکن است staff.id باشد یا organization_staff_id — هر دو را چک می‌کنیم
        if (this.staffId) {
          const found = this.staffList.find(
            s => String(s.organization_staff_id ?? s.id) === String(this.staffId) ||
                 String(s.id) === String(this.staffId)
          );
          if (found) this.staffId = String(found.organization_staff_id ?? found.id);
        }

        // Normalize serviceId
        if (this.organizationServicesId) {
          const found = this.serviceList.find(
            s => String(s.organization_service_id ?? s.id) === String(this.organizationServicesId) ||
                 String(s.id) === String(this.organizationServicesId)
          );
          if (found) this.organizationServicesId = String(found.organization_service_id ?? found.id);
        }

        this.isLoadingData = false;

        if (this.staffId && this.organizationServicesId && this.selectedDate) {
          this.fetchSlots(this.selectedDate);
        }
      },
      error: () => { this.isLoadingData = false; },
    });

    if (!this.isUserMode) {
      this.authHttpService.listUsers({ is_paginate: false }).subscribe({
        next: (res: any) => {
          this.userList = res.data || [];
          if (!this.selectedUserId) this.fetchCurrentUser();
        },
      });
    }
  }

  checkAndFetchSlots() {
    if (this.selectedDate && this.staffId && this.organizationServicesId) {
      this.fetchSlots(this.selectedDate);
    }
  }

  fetchSlots(date: Date): void {
    if (!this.staffId || !this.organizationServicesId) return;

    this.isLoadingSlots = true;

    this.indexHttpService.getAvailableSlots({
      date:       this.formatDate(date),
      staff_id:   String(this.staffId),
      service_id: String(this.organizationServicesId),
    }).subscribe({
      next: (res) => {
        this.availableSlots = res.data || [];

        // Restore a time that came from query param or edit mode
        const target = this.pendingSlotTime;
        if (target) {
          if (!this.availableSlots.find(s => s.start_time === target)) {
            this.availableSlots.push({ start_time: target, end_time: '' });
            this.availableSlots.sort((a, b) => a.start_time.localeCompare(b.start_time));
          }
          this.selectedSlot    = this.availableSlots.find(s => s.start_time === target) ?? null;
          this.pendingSlotTime = null;
        } else if (this.isEditMode && this.selectedSlot) {
          const t = this.selectedSlot.start_time;
          if (!this.availableSlots.find(s => s.start_time === t)) {
            this.availableSlots.push(this.selectedSlot);
            this.availableSlots.sort((a, b) => a.start_time.localeCompare(b.start_time));
          }
          this.selectedSlot = this.availableSlots.find(s => s.start_time === t) ?? null;
        }

        this.isLoadingSlots = false;
      },
      error: () => {
        this.toastService.error('خطا در دریافت زمان‌های خالی');
        this.isLoadingSlots = false;
      },
    });
  }

  selectSlot(slot: any): void {
    this.selectedSlot = slot;
  }

  toggleResource(resourceId: string): void {
    const idx = this.selectedResourceIds.indexOf(resourceId);
    if (idx > -1) this.selectedResourceIds.splice(idx, 1);
    else this.selectedResourceIds.push(resourceId);
  }

  bookAppointment(): void {
    if (!this.selectedSlot || !this.selectedDate) return;
    if (!this.selectedUserId) {
      this.toastService.error('لطفاً مشتری را انتخاب کنید');
      return;
    }

    this.isBooking = true;
    const data = {
      user_id:                 this.selectedUserId,
      staff_id:                this.staffId,
      service_id:              this.organizationServicesId,
      date_of_turn:            this.formatDate(this.selectedDate),
      start_time:              this.selectedSlot.start_time,
      type:                    'Online',
      permissible_interference: false,
      resource_ids:            this.selectedResourceIds,
    };

    const req = this.isEditMode && this.editingAppointmentId
      ? this.panelHttpService.editAppointment(this.editingAppointmentId, data)
      : this.indexHttpService.addAppointment(data);

    req.subscribe({
      next: () => {
        this.toastService.success(this.isEditMode ? 'نوبت با موفقیت ویرایش شد' : 'نوبت شما با موفقیت ثبت شد');
        this.isBooking    = false;
        this.selectedSlot = null;
        if (this.isEditMode) this.router.navigate(['/panel/dashboard']);
        else this.fetchSlots(this.selectedDate!);
      },
      error: (err: any) => {
        this.toastService.error(err.message || 'خطا در ثبت نوبت');
        this.isBooking = false;
      },
    });
  }

  loadAppointmentForEdit(id: string | number) {
    this.isEditMode           = true;
    this.editingAppointmentId = id;

    this.panelHttpService.getAppointmentDetails(String(id)).subscribe({
      next: (res: any) => {
        const app = res.data;
        this.selectedDate           = new Date(app.date_of_turn);
        this.staffId                = String(app.staff_id);
        this.organizationServicesId = String(app.service_id);
        this.selectedUserId         = String(app.user_id ?? app.user?.id ?? app.user ?? '');
        this.selectedResourceIds    = app.resources ? app.resources.map((r: any) => String(r.id)) : [];
        this.hasStaffParam   = true;
        this.hasServiceParam = true;

        if (app.start_time) {
          this.pendingSlotTime = app.start_time.substring(0, 5);
          this.selectedSlot    = { start_time: this.pendingSlotTime, end_time: app.end_time?.substring(0, 5) ?? '' };
        }

        this.loadInitialData();
      },
    });
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
