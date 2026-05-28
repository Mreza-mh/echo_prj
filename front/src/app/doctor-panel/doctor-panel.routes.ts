import { Routes } from '@angular/router';
import { DoctorPanelComponent } from './doctor-panel-layout.component';
import { DoctorSettingsComponent } from './settings/settings.component';

export const routes: Routes = [
  {
    path: '',
    component: DoctorPanelComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./doctor-dashboard/doctor-dashboard.component').then(m => m.DoctorDashboardComponent)
      },
      {
        path: 'echo-history',
        loadComponent: () => import('./echo-history/echo-history.component').then(m => m.EchoHistoryComponent)
      },
      {
        path: 'settings',
        component: DoctorSettingsComponent
      },
    ],
  },
];