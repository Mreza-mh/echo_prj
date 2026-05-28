import { Routes } from '@angular/router';
import { IndexComponent } from './index.component';

export const routes: Routes = [
  {
    path: '',
    component: IndexComponent,
    children: [
      {
        path: '',
        redirectTo: 'home',
        pathMatch: 'full',
      },
      {
        path: 'home',
        loadComponent: () => import('./home/home.component').then((m) => m.HomeComponent),
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./user-dashboard/user-dashboard.component').then((m) => m.UserDashboardComponent),
      },
      {
        path: 'about',
        loadComponent: () => import('./about/about.component').then((m) => m.AboutComponent),
      },
      {
        path: 'contact',
        loadComponent: () => import('./contact/contact.component').then((m) => m.ContactComponent),
      },
      {
        path: 'appointment',
        loadComponent: () =>
          import('./appointment/appointment.component').then((m) => m.AppointmentComponent),
      },
      {
        path: 'appointment/:organid',
        loadComponent: () =>
          import('./appointment/appointment.component').then((m) => m.AppointmentComponent),
      },
      {
        path: 'appointment/:organid/:staffid',
        loadComponent: () =>
          import('./appointment/appointment.component').then((m) => m.AppointmentComponent),
      },
      {
        path: 'organizations',
        loadComponent: () =>
          import('./organization-services/organization-services.component').then(
            (m) => m.OrganizationServicesComponent,
          ),
      },
      {
        path: 'organization-services/:id',
        loadComponent: () =>
          import('./organization-services/organization-services.component').then(
            (m) => m.OrganizationServicesComponent,
          ),
      },
      {
        path: 'staff-details/:id',
        loadComponent: () =>
          import('./staff-details/staff-details.component').then((m) => m.StaffDetailsComponent),
      },
      {
        path: 'profile',
        loadComponent: () => import('./profile/profile.component').then((m) => m.ProfileComponent),
      },
    ],
  },
];
