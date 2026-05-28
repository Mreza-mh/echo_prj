import { Component, OnInit, inject, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { PanelHttpService } from '../panel-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { format, parseISO } from 'date-fns';
import { Router } from '@angular/router';

// FullCalendar Imports
import { FullCalendarModule, FullCalendarComponent } from '@fullcalendar/angular';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';
import resourceTimelinePlugin from '@fullcalendar/resource-timeline';
import { PanelService } from '../panel.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatIconModule,
    MatButtonModule,
    FullCalendarModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  @ViewChild('calendar') calendarComponent!: FullCalendarComponent;

  private panelHttp = inject(PanelHttpService);
  private panelService = inject(PanelService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  selectedDate: Date = new Date();
  filterStaffIds: number[] = [];
  filterResourceIds: number[] = [];

  staffs: any[] = [];
  resources: any[] = [];
  dashboardData: any = null;
  allAppointments: any[] = [];
  isLoading = false;

  // FullCalendar Options
  calendarOptions: CalendarOptions = {
    plugins: [resourceTimelinePlugin, interactionPlugin, dayGridPlugin, timeGridPlugin, listPlugin],
    initialView: 'resourceTimelineDay',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'resourceTimelineDay,timeGridWeek,dayGridMonth,listWeek',
    },
    resourceAreaHeaderContent: 'پرسنل و منابع',
    resourceAreaWidth: '200px',
    slotMinTime: '07:00:00',
    slotMaxTime: '23:00:00',
    locale: 'fa',
    direction: 'rtl',
    firstDay: 6,
    height: '650px',
    nowIndicator: true,
    editable: true,
    selectable: true,
    // Flexible constraints to allow "shooting" patients around
    eventConstraint: {
      startTime: '00:00',
      endTime: '24:00',
    },
    selectConstraint: {
      startTime: '00:00',
      endTime: '24:00',
    },
    eventDrop: this.onEventDrop.bind(this),
    dateClick: (info) => {
      this.onDateClick(info);
    },
    eventClick: (info) => {
      this.onEventClick(info);
    },
    eventDidMount: (info) => {
      const status = info.event.extendedProps['status_title'];
      if (status && info.event.display !== 'background') {
        info.el.classList.add(`event-status-${status}`);
      }
    },
    resourceLabelDidMount: (info) => {
      const expertise = info.resource.extendedProps['expertise'];
      const mainCell = info.el.querySelector('.fc-datagrid-cell-main') as HTMLElement;
      if (mainCell && expertise) {
        const subTitle = document.createElement('div');
        subTitle.className = 'resource-expertise-sub';
        subTitle.style.fontSize = '0.7rem';
        subTitle.style.color = '#64748b';
        subTitle.style.fontWeight = '400';
        subTitle.innerText = expertise;
        mainCell.appendChild(subTitle);
      }
    },
  };

  ngOnInit() {
    this.loadInitialFilters();
    this.loadData();
  }

  onEventDrop(info: any) {
    const event = info.event;
    const newStaffId = info.newResource ? info.newResource.id : event.resourceId;
    const newStart = format(event.start, 'HH:mm');
    const newDate = format(event.start, 'yyyy-MM-dd');
    const appointmentId = event.id;
    const extendedProps = event.extendedProps;

    // Proactive update: move "patient" around (shout it!)
    this.isLoading = true;

    const updateData = {
      user_id: extendedProps.user_id || 1, // Fallback if missing, but should be in props
      staff_id: Number(newStaffId),
      service_id: extendedProps.service_id || 1,
      date_of_turn: newDate,
      start_time: newStart,
      type: extendedProps.type || 'Online',
      permissible_interference: false,
      resource_ids: extendedProps.resource_ids || [],
    };

    this.panelHttp.editAppointment(appointmentId, updateData).subscribe({
      next: (res: any) => {
        this.toast.success('نوبت با موفقیت جابجا شد');
        this.loadData(); // Refresh to ensure everything is synced
      },
      error: (err: any) => {
        info.revert(); // Put it back if API fails
        this.isLoading = false;
        this.toast.error(err.message || 'خطا در جابجایی نوبت');
      },
    });
  }

  private toast = inject(ToastService);

  loadInitialFilters() {
    this.panelHttp.getStaffList({ is_paginate: false }).subscribe((res: any) => {
      this.staffs = res.data || [];
    });
    this.panelHttp.getResourceList({ is_paginate: false }).subscribe((res: any) => {
      this.resources = res.data || [];
    });
  }

  loadData() {
    this.isLoading = true;
    const dateStr = format(this.selectedDate, 'yyyy-MM-dd');

    this.panelHttp
      .getCalendarDashboard({
        date: dateStr,
        staff_ids: this.filterStaffIds.length > 0 ? this.filterStaffIds : undefined,
        resource_ids: this.filterResourceIds.length > 0 ? this.filterResourceIds : undefined,
      })
      .subscribe({
        next: (res: any) => {
          this.dashboardData = res.data;
          this.isLoading = false;
          this.cdr.detectChanges(); // Trigger detection so @if is evaluated
          this.updateCalendarData();
        },
        error: (err: any) => {
          this.isLoading = false;
          this.toast.error('خطا در بارگذاری اطلاعات');
        },
      });
  }

  private updateCalendarData() {
    if (!this.dashboardData) return;

    // Small timeout to ensure ViewChild is populated if @if just became true
    setTimeout(() => {
      const calendarApi = this.calendarComponent?.getApi();

      // 1. Prepare Resources (Staff)
      const resources = this.dashboardData.timeline.map((staff: any) => ({
        id: String(staff.staff_id),
        title: staff.staff_name,
        extendedProps: {
          expertise: staff.expertise,
          working_hours: staff.working_hours,
        },
      }));

      // 2. Prepare Events
      const events: EventInput[] = [];
      this.allAppointments = [];

      // Track min/max hours to adjust view
      let minHour = 24;
      let maxHour = 0;

      this.dashboardData.timeline.forEach((staff: any) => {
        // Update min/max from working hours
        if (staff.working_hours) {
          const startH = parseInt(staff.working_hours.start.split(':')[0]);
          const endH = parseInt(staff.working_hours.end.split(':')[0]);
          if (startH < minHour) minHour = startH;
          if (endH > maxHour) maxHour = endH;

          // Add Working Hours as Background (Green area)
          events.push({
            resourceId: String(staff.staff_id),
            start: `${this.dashboardData.date}T${staff.working_hours.start}:00`,
            end: `${this.dashboardData.date}T${staff.working_hours.end}:00`,
            display: 'background',
            backgroundColor: 'rgba(16, 185, 129, 0.12)', // Subtle green
            groupId: 'businessHours', // Constraint link
          });
        }

        if (staff.appointments) {
          staff.appointments.forEach((app: any) => {
            this.allAppointments.push({
              ...app,
              staff_name: staff.staff_name,
            });

            events.push({
              id: String(app.id),
              resourceId: String(staff.staff_id),
              title: `${app.customer_name} - ${app.service_name}`,
              start: `${this.dashboardData.date}T${app.start}`,
              end: `${this.dashboardData.date}T${app.end}`,
              backgroundColor: this.getStatusColor(app.status_title),
              borderColor: this.getStatusColor(app.status_title),
              extendedProps: {
                ...app,
                staff_name: staff.staff_name,
              },
            });
          });
        }
      });

      this.allAppointments.sort((a, b) => a.start.localeCompare(b.start));

      // Dynamic slot adjustment
      const slotMin =
        Math.max(0, minHour - 1)
          .toString()
          .padStart(2, '0') + ':00:00';
      const slotMax =
        Math.min(24, maxHour + 1)
          .toString()
          .padStart(2, '0') + ':00:00';

      this.calendarOptions = {
        ...this.calendarOptions,
        resources: resources,
        events: events,
        slotMinTime: slotMin === '23:00:00' ? '08:00:00' : slotMin,
        slotMaxTime: slotMax === '01:00:00' ? '22:00:00' : slotMax,
      };

      if (calendarApi) {
        calendarApi.gotoDate(this.dashboardData.date);
      }

      this.cdr.detectChanges();
    }, 0);
  }

  private getStatusColor(status: string): string {
    switch (status) {
      case 'pending':
        return '#f59e0b';
      case 'confirmed':
        return '#10b981';
      case 'cancelled':
        return '#ef4444';
      case 'completed':
        return '#6366f1';
      default:
        return '#94a3b8';
    }
  }

  onEventClick(info: any) {
    const appointmentId = info.event.id;
    if (appointmentId) {
      window.open(`/appointment?edit_id=${appointmentId}`, '_blank');
    }
  }

  onDateClick(info: any) {
    const staffId = info.resource ? info.resource.id : '';
    const dateStr = format(info.date, 'yyyy-MM-dd');
    const timeStr = format(info.date, 'HH:mm');
    
    let url = `/appointment?&date=${dateStr}&time=${timeStr}`;
    if (staffId) {
      url += `&staff_id=${staffId}`;
    }
    window.open(url, '_blank');
  }

  onAppointmentClick(app: any) {
    window.open(`/appointment?edit_id=${app.id}`, '_blank');
  }

  onAddAppointment() {
    window.open(`/appointment?`, '_blank');
  }
}