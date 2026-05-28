import { Routes } from '@angular/router';
import { authGuard } from '../@shared/guards/auth.guard';
import { SuperPanelManagementComponent } from './super-panel.component';

export const routes: Routes = [
  {
    path: '',
    component: SuperPanelManagementComponent,
    children: [
      {
        path: '',
        redirectTo: 'users',
        pathMatch: 'full',
      },
      {
        path: 'users',
        loadComponent: () => import('./users/users.component').then((m) => m.UsersComponent),
      },
      {
        path: 'organizations',
        loadComponent: () => import('./organizations/organizations.component').then((m) => m.OrganizationsComponent),
      },
      {
        path: 'services',
        loadComponent: () => import('./services/services.component').then((m) => m.ServicesComponent),
      },
    ],
  },
];
