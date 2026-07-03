import { Routes } from '@angular/router';
import { PanelComponent } from './panel.component';
import { authGuard } from '../@shared/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    component: PanelComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'staff',
        loadComponent: () => import('./staff/staff').then(m => m.StaffComponent)
      },
      {
        path: 'staff-schedule',
        loadComponent: () => import('./staff-schedule/staff-schedule').then(m => m.StaffScheduleComponent)
      },
      {
        path: 'organization-service',
        loadComponent: () => import('./organization-service/organization-service').then(m => m.OrganizationServiceComponent)
      },
      {
        path: 'resource',
        loadComponent: () => import('./resource/resource').then(m => m.ResourceComponent)
      },
      // بخش status مشکل دارد و موقتاً از فرانت مخفی شده
      // {
      //   path: 'status',
      //   loadComponent: () => import('./status/status').then(m => m.StatusComponent)
      // },
      {
        path: 'expertise',
        loadComponent: () => import('./expertise/expertise').then(m => m.ExpertiseComponent)
      },
      {
        path: 'appointment',
        loadComponent: () => import('../index/appointment/appointment.component').then(m => m.AppointmentComponent)
      },
      {
        path: 'settings',
        loadComponent: () => import('./settings/settings.component').then(m => m.SettingsComponent)
      },
      {
        path: 'vital-monitor',
        loadComponent: () => import('./vital-monitor/vital-monitor.component').then(m => m.VitalMonitorComponent)
      },
    ],
  },
];

